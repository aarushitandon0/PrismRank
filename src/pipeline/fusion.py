"""
Score fusion module.

JD-specific context (Senior AI Engineer — Redrob AI):
  Hard requirements: embeddings retrieval, vector DB, Python, eval frameworks (NDCG/MRR)
  Disqualifiers: consulting-only career, non-tech titles with AI claims, research-only background
  Boosts: product company experience, active on platform, India/willing-to-relocate, NLP/IR background
  Down-weight: inactive > 6 months + low response rate, notice > 30 days, pure CV/speech/robotics
"""

import re
from datetime import date, datetime
import pandas as pd
from src.config import SCORE_WEIGHTS, FINAL_SHORTLIST

_CONSULTING_FIRMS = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini",
    "hcl", "tech mahindra", "mphasis", "hexaware", "mindtree", "ltimindtree",
    "ibm", "cts", "dxc", "ntt data",
}

_INDIA_LOCATIONS = {
    "pune", "noida", "delhi", "bangalore", "bengaluru", "hyderabad",
    "mumbai", "chennai", "gurugram", "gurgaon", "india",
}

_CORE_JD_SKILLS = {
    "embedding", "embeddings", "sentence-transformers", "faiss", "pinecone",
    "milvus", "weaviate", "qdrant", "vector", "retrieval", "ranking",
    "nlp", "information retrieval", "ndcg", "mrr", "a/b testing",
    "python", "llm", "fine-tuning", "lora", "qlora", "peft",
    "hybrid search", "bge", "e5", "openai embeddings",
}

_NONTECHNICAL_KEYWORDS = {
    "marketing", "sales", "accountant", "finance", "hr", "human resources",
    "operations", "customer support", "civil engineer", "mechanical engineer",
    "graphic designer", "content writer",
}


def _redrob_signal_score(features: dict) -> float:
    redrob = features.get("redrob", {})
    score = 0.0

    completeness = (redrob.get("profile_completeness_score") or 0) / 100.0
    score += completeness * 0.4

    if redrob.get("open_to_work_flag"):
        score += 0.15

    notice = redrob.get("notice_period_days", 60) or 60
    if notice <= 30:
        score += 0.20
    elif notice <= 60:
        score += 0.10
    elif notice <= 90:
        score += 0.05

    views = redrob.get("profile_views_received_30d", 0) or 0
    score += min(views / 50.0, 0.15)
    score += min((redrob.get("applications_submitted_30d", 0) or 0) / 20.0, 0.10)

    return min(score, 1.0)


def _jd_specific_modifier(features: dict, raw: dict) -> tuple[float, list[str]]:
    """
    Returns (multiplier, reasons_list).
    Multiplier < 1.0 = penalty, > 1.0 = boost, 1.0 = neutral.
    Applied after weighted score.
    """
    multiplier = 1.0
    reasons = []
    redrob = features.get("redrob", {})
    career = features.get("career_history", [])
    skills_list = [s.lower() for s in features.get("skills_list", [])]
    title = (features.get("current_title") or "").lower()
    location = (features.get("location") or "").lower()
    country = (features.get("country") or "").lower()
    yoe = float(features.get("years_experience", 0) or 0)

    # ── Hard disqualifiers (JD explicit) ──────────────────────────────────

    # 1. Consulting-only career — JD says: "people who have only worked at consulting firms"
    all_companies = [r.get("company", "").lower() for r in career]
    non_consulting_exists = any(
        not any(f in co for f in _CONSULTING_FIRMS) for co in all_companies if co
    )
    if all_companies and not non_consulting_exists:
        multiplier *= 0.50
        reasons.append("Consulting-only career (explicit JD disqualifier)")

    # 2. Non-technical title with AI keyword claims — the "trap" the JD warns about
    title_is_nontechnical = any(nt in title for nt in _NONTECHNICAL_KEYWORDS)
    claimed_core_skills = sum(1 for s in skills_list if any(cs in s for cs in _CORE_JD_SKILLS))
    if title_is_nontechnical and claimed_core_skills >= 3:
        multiplier *= 0.45
        reasons.append(f"Title-skill trap: '{features.get('current_title','')}' claiming {claimed_core_skills} AI/ML skills")

    # 3. Pure CV/Speech/Robotics without NLP/IR
    cv_speech = {"computer vision", "speech recognition", "object detection", "tts", "asr", "robotics"}
    has_cv_speech = sum(1 for s in skills_list if s in cv_speech) >= 3
    has_nlp_ir = any(s in skills_list for s in ["nlp", "information retrieval", "ranking", "retrieval", "embeddings"])
    if has_cv_speech and not has_nlp_ir:
        multiplier *= 0.70
        reasons.append("CV/Speech specialist without NLP/IR background (JD disqualifier)")

    # 4. Activity ghost — inactive > 180 days + low response rate
    last_active = redrob.get("last_active_date")
    if last_active:
        try:
            la_date = datetime.strptime(last_active, "%Y-%m-%d").date()
            days_inactive = (date.today() - la_date).days
            rr = redrob.get("recruiter_response_rate") or 0
            if days_inactive > 180 and rr < 0.15:
                multiplier *= 0.75
                reasons.append(f"Activity ghost: inactive {days_inactive}d + {rr:.0%} response rate")
            elif days_inactive > 90 and rr < 0.1:
                multiplier *= 0.85
                reasons.append(f"Low activity: inactive {days_inactive}d + {rr:.0%} response rate")
        except Exception:
            pass

    # ── Boosts (JD-specific positives) ────────────────────────────────────

    # 5. India location boost (Pune/Noida/major city preferred)
    in_india = country == "india" or any(loc in location for loc in _INDIA_LOCATIONS)
    willing_to_relocate = bool(redrob.get("willing_to_relocate"))
    if in_india:
        multiplier = min(multiplier * 1.08, 1.0)
        reasons.append("India-based (preferred location)")
    elif willing_to_relocate:
        multiplier = min(multiplier * 1.03, 1.0)
        reasons.append("Willing to relocate")

    # 6. Product company background boost (vs services-only)
    service_industries = {"it services", "consulting", "outsourcing", "staffing"}
    has_product_company = any(
        r.get("industry", "").lower() not in service_industries
        and not any(f in r.get("company", "").lower() for f in _CONSULTING_FIRMS)
        for r in career
    )
    if has_product_company:
        multiplier = min(multiplier * 1.05, 1.0)
        reasons.append("Product company experience")

    # 7. Sub-30-day notice boost (JD says "we'd love sub-30-day notice")
    notice = redrob.get("notice_period_days", 60) or 60
    if notice <= 30:
        multiplier = min(multiplier * 1.04, 1.0)
        reasons.append("Sub-30-day notice")
    elif notice > 60:
        multiplier *= 0.97

    # 8. Core JD skill match boost — real NLP/IR/ranking background
    core_matches = sum(1 for s in skills_list if any(cs in s for cs in _CORE_JD_SKILLS))
    if core_matches >= 5:
        multiplier = min(multiplier * 1.07, 1.0)
        reasons.append(f"Strong core skill match ({core_matches} JD-critical skills)")
    elif core_matches >= 3:
        multiplier = min(multiplier * 1.03, 1.0)

    # 9. YoE range fit — JD says 5-9 years (flexible)
    if 4 <= yoe <= 10:
        multiplier = min(multiplier * 1.02, 1.0)
    elif yoe < 2 or yoe > 18:
        multiplier *= 0.92

    return round(multiplier, 4), reasons


def compute_final_score(candidate: dict, jd_parsed: dict) -> dict:
    f = candidate.get("features", {})
    llm = candidate.get("llm", {})
    traj = candidate.get("trajectory", {})
    behavioral = candidate.get("behavioral_score", 0.5)
    honeypot = candidate.get("honeypot", {})

    skill_alignment = float(llm.get("skill_alignment", 0.5))
    experience_fit = float(llm.get("experience_fit", 0.5))
    culture_fit = float(llm.get("culture_fit", 0.5))
    gap_alert = llm.get("gap_alert") or ""
    standout = llm.get("standout_signal") or ""

    redrob_score = _redrob_signal_score(f)
    trajectory_percentile = traj.get("trajectory_percentile", 50) if traj else 50
    trajectory_label = traj.get("trajectory_label", "Unknown") if traj else "Unknown"

    # ── Weighted base score ───────────────────────────────────────────────
    weighted = (
        skill_alignment * SCORE_WEIGHTS["skill_match"]
        + experience_fit * SCORE_WEIGHTS["experience_fit"]
        + behavioral * SCORE_WEIGHTS["behavioral"]
        + redrob_score * SCORE_WEIGHTS["redrob_signals"]
        + culture_fit * SCORE_WEIGHTS["culture_soft"]
    )

    # ── Standard modifiers ────────────────────────────────────────────────
    deal_breakers = [db.lower() for db in (jd_parsed.get("deal_breakers") or [])]
    if gap_alert and deal_breakers:
        gap_lower = gap_alert.lower()
        if any(db in gap_lower for db in deal_breakers):
            weighted *= 0.6

    if trajectory_percentile > 85:
        weighted = min(weighted * 1.08, 1.0)

    assessment_scores = f.get("skill_assessment_scores", {})
    hard_skills = [s.lower() for s in (jd_parsed.get("hard_skills") or [])]
    matched_assessments = [
        v for k, v in assessment_scores.items()
        if k.lower() in hard_skills and isinstance(v, (int, float))
    ]
    if len(matched_assessments) >= 2 and (sum(matched_assessments) / len(matched_assessments)) > 75:
        weighted = min(weighted * 1.05, 1.0)

    redrob = f.get("redrob", {})
    if not redrob.get("open_to_work_flag") and (redrob.get("notice_period_days") or 0) > 90:
        weighted *= 0.95

    # ── JD-specific modifiers ─────────────────────────────────────────────
    jd_multiplier, jd_reasons = _jd_specific_modifier(f, candidate.get("raw", {}))
    weighted = weighted * jd_multiplier

    # ── Honeypot penalty ──────────────────────────────────────────────────
    honeypot_score = honeypot.get("honeypot_score", 0.0)
    if honeypot_score > 0:
        honeypot_multiplier = 1.0 - (honeypot_score * 0.8)
        weighted *= honeypot_multiplier

    weighted = round(min(max(weighted, 0.0), 1.0), 4)

    exceptional_fit = behavioral > 0.8 and skill_alignment > 0.85 and honeypot_score < 0.2

    if weighted >= 0.78:
        tier = "A"
    elif weighted >= 0.58:
        tier = "B"
    else:
        tier = "C"

    # ── Reasoning string for submission.csv ───────────────────────────────
    top_skills = f.get("top_skills", [])[:3]
    name = f.get("name", "Candidate")
    yoe = f.get("years_experience", 0)
    gap_str = f" Gap: {gap_alert[:60]}." if gap_alert else ""
    standout_str = f" Standout: {standout[:60]}." if standout else ""
    hp_str = f" ⚠ Honeypot flags: {len(honeypot.get('flags', []))}." if honeypot_score > 0.3 else ""
    reasoning = (
        f"{name} | {yoe}yr exp | Skills: {', '.join(top_skills)} | "
        f"Skill fit {skill_alignment:.2f}, Exp fit {experience_fit:.2f}, "
        f"Behavioral {behavioral:.2f}, Trajectory: {trajectory_label}.{gap_str}{standout_str}{hp_str}"
    )
    if len(reasoning) > 200:
        reasoning = reasoning[:197] + "..."

    return {
        **candidate,
        "final_score": weighted,
        "tier": tier,
        "exceptional_fit": exceptional_fit,
        "reasoning": reasoning,
        "jd_reasons": jd_reasons,
        "honeypot_score": honeypot_score,
        "honeypot_flags": honeypot.get("flags", []),
        "weighted_breakdown": {
            "skill_alignment": skill_alignment,
            "experience_fit": experience_fit,
            "behavioral": behavioral,
            "redrob_signals": redrob_score,
            "culture_fit": culture_fit,
        },
        "trajectory_label": trajectory_label,
        "trajectory_percentile": trajectory_percentile,
        "one_line_summary": llm.get("one_line_summary", ""),
        "gap_alert": gap_alert or None,
        "standout_signal": standout or None,
    }


def rank_all(candidates: list[dict]) -> pd.DataFrame:
    rows = []
    for c in candidates:
        f = c.get("features", {})
        rows.append({
            "candidate_id": f.get("candidate_id", ""),
            "name": f.get("name", ""),
            "final_score": c.get("final_score", 0.0),
            "tier": c.get("tier", "C"),
            "exceptional_fit": c.get("exceptional_fit", False),
            "reasoning": c.get("reasoning", ""),
            "skill_alignment": c.get("weighted_breakdown", {}).get("skill_alignment", 0.5),
            "experience_fit": c.get("weighted_breakdown", {}).get("experience_fit", 0.5),
            "behavioral_score": c.get("behavioral_score", 0.0),
            "redrob_signals": c.get("weighted_breakdown", {}).get("redrob_signals", 0.0),
            "culture_fit": c.get("weighted_breakdown", {}).get("culture_fit", 0.5),
            "trajectory_label": c.get("trajectory_label", "Unknown"),
            "trajectory_percentile": c.get("trajectory_percentile", 50),
            "one_line_summary": c.get("one_line_summary", ""),
            "gap_alert": c.get("gap_alert"),
            "standout_signal": c.get("standout_signal"),
            "top_skills": f.get("top_skills", []),
            "years_experience": f.get("years_experience", 0),
            "current_title": f.get("current_title", ""),
            "current_company": f.get("current_company", ""),
            "location": f.get("location", ""),
            "country": f.get("country", ""),
            "education_tier_score": f.get("education_tier_score", 1),
            "open_to_work": f.get("open_to_work", False),
            "notice_period_days": (f.get("redrob", {}) or {}).get("notice_period_days", 60),
            "preferred_work_mode": (f.get("redrob", {}) or {}).get("preferred_work_mode", "any"),
            "willing_to_relocate": (f.get("redrob", {}) or {}).get("willing_to_relocate", False),
            "skill_assessment_scores": f.get("skill_assessment_scores", {}),
            "honeypot_score": c.get("honeypot_score", 0.0),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values(["final_score", "candidate_id"], ascending=[False, True])
    df = df.reset_index(drop=True)
    df["rank"] = df.index + 1
    return df
