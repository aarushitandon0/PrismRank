"""
Honeypot & trap candidate detector.

The challenge dataset contains ~80 honeypots with subtly impossible profiles.
Any submission with > 10% honeypot rate in top-100 is DISQUALIFIED.

Detection signals:
  1. Temporal impossibility  — YoE vs education graduation gap
  2. Title-skill mismatch    — Non-technical titles claiming expert ML skills
  3. Signal saturation       — Multiple behavioral signals simultaneously maxed
  4. Assessment suspicion    — All scores identical or impossibly consistent
  5. Keyword stuffing        — AI keywords with zero supporting career history
  6. Consulting-only career  — JD explicitly disqualifies these
  7. Low activity score      — Hasn't been active + low response rate
"""

import re
from datetime import date, datetime

_CONSULTING_FIRMS = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini",
    "hcl", "tech mahindra", "mphasis", "hexaware", "mindtree", "ltimindtree",
    "ibm", "cts", "dxc", "ntt data", "unisys", "conduent",
}

_NONTECHNICAL_TITLES = {
    "marketing", "sales", "accountant", "accounting", "finance",
    "hr manager", "human resources", "operations manager", "customer support",
    "business analyst", "project manager", "content writer",
    "graphic designer", "civil engineer", "mechanical engineer",
    "teacher", "lawyer", "doctor",
}

_AI_ML_SKILLS = {
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "llm", "fine-tuning", "rag", "embeddings",
    "pytorch", "tensorflow", "transformers", "bert", "gpt",
    "neural network", "image classification", "speech recognition",
    "object detection", "recommendation", "ranking",
}

_SERVICES_INDUSTRY_KEYWORDS = {"it services", "consulting", "outsourcing", "bpo"}


def detect_honeypot(features: dict) -> dict:
    """
    Returns {
        "is_honeypot": bool,
        "honeypot_score": float,  # 0-1, higher = more suspicious
        "flags": list[str],
    }
    """
    flags = []
    penalty = 0.0

    redrob = features.get("redrob", {})
    career = features.get("career_history", [])
    skills_prof = features.get("skills_proficiency", {})
    assessment = features.get("skill_assessment_scores", {})
    yoe = float(features.get("years_experience", 0) or 0)
    title = (features.get("current_title") or "").lower()
    company = (features.get("current_company") or "").lower()

    # ── 1. Temporal impossibility ──────────────────────────────────────────
    education = features.get("education", [])
    if education and yoe > 0:
        grad_years = [e.get("end_year") for e in education if e.get("end_year")]
        if grad_years:
            earliest_grad = min(grad_years)
            current_year = date.today().year
            max_possible_yoe = current_year - earliest_grad
            # If claimed YoE > 3 years more than possible since graduation
            if yoe > max_possible_yoe + 3:
                flags.append(
                    f"Temporal impossibility: claims {yoe}yr exp but graduated {earliest_grad} "
                    f"(max possible ~{max_possible_yoe}yr)"
                )
                penalty += 0.45

    # ── 2. Title–skill mismatch ────────────────────────────────────────────
    title_is_nontechnical = any(nt in title for nt in _NONTECHNICAL_TITLES)
    if title_is_nontechnical:
        advanced_ai = sum(
            1 for skill, prof in skills_prof.items()
            if skill.lower() in _AI_ML_SKILLS and prof >= 3  # advanced or expert
        )
        if advanced_ai >= 3:
            flags.append(
                f"Title-skill mismatch: '{title}' claims {advanced_ai} advanced AI/ML skills"
            )
            penalty += 0.35

    # ── 3. Signal saturation ───────────────────────────────────────────────
    sat_checks = {
        "profile_completeness": (redrob.get("profile_completeness_score") or 0) >= 98,
        "github": (redrob.get("github_activity_score") or -1) >= 95,
        "interview_rate": (redrob.get("interview_completion_rate") or 0) >= 0.99,
        "response_rate": (redrob.get("recruiter_response_rate") or 0) >= 0.99,
        "verified": redrob.get("verified_email") and redrob.get("verified_phone") and redrob.get("linkedin_connected"),
        "saved": (redrob.get("saved_by_recruiters_30d") or 0) >= 50,
    }
    sat_count = sum(sat_checks.values())
    if sat_count >= 5:
        flags.append(f"Signal saturation: {sat_count}/6 behavioral signals simultaneously maxed")
        penalty += 0.30

    # ── 4. Assessment score suspicion ─────────────────────────────────────
    if len(assessment) >= 3:
        vals = [v for v in assessment.values() if isinstance(v, (int, float))]
        if vals:
            if all(v == 100 for v in vals):
                flags.append("All skill assessments scored 100.0 — statistically implausible")
                penalty += 0.40
            elif len(vals) >= 3:
                # Suspiciously narrow range (all within 2 points of each other)
                spread = max(vals) - min(vals)
                if spread < 2 and len(vals) >= 4:
                    flags.append(f"Assessment scores suspiciously uniform (spread={spread:.1f} across {len(vals)} skills)")
                    penalty += 0.20

    # ── 5. Keyword stuffing without supporting career ──────────────────────
    skill_names = {s.lower() for s in features.get("skills_list", [])}
    claimed_ai = skill_names & _AI_ML_SKILLS
    if claimed_ai:
        # Check if any career role is AI/tech-adjacent
        career_descriptions = " ".join(
            (r.get("description") or "") + " " + (r.get("title") or "")
            for r in career
        ).lower()
        has_ml_career = any(kw in career_descriptions for kw in [
            "machine learning", "deep learning", "model", "neural", "nlp",
            "data science", "ml", "ai", "embedding", "training", "inference",
            "pytorch", "tensorflow", "spark", "pipeline", "analytics",
        ])
        if not has_ml_career and len(claimed_ai) >= 5:
            flags.append(
                f"Keyword stuffing: {len(claimed_ai)} AI/ML skills claimed but zero supporting career evidence"
            )
            penalty += 0.40

    # ── 6. Consulting-only career ─────────────────────────────────────────
    # (Not a honeypot per se, but JD explicit disqualifier)
    all_companies = [r.get("company", "").lower() for r in career]
    all_consulting = all(
        any(firm in co for firm in _CONSULTING_FIRMS) for co in all_companies if co
    )
    if all_consulting and len(all_companies) >= 2:
        flags.append(
            "Consulting-only career (JD explicit disqualifier: never worked at product company)"
        )
        penalty += 0.25  # Penalty but not instant disqualification (some are borderline)

    # ── 7. Extremely low platform activity despite claiming job-seeking ────
    last_active = redrob.get("last_active_date")
    if last_active and redrob.get("open_to_work_flag"):
        try:
            la_date = datetime.strptime(last_active, "%Y-%m-%d").date()
            days_inactive = (date.today() - la_date).days
            rr = redrob.get("recruiter_response_rate") or 0
            if days_inactive > 180 and rr < 0.1:
                flags.append(
                    f"Ghost candidate: claims open-to-work but inactive {days_inactive} days, "
                    f"response rate {rr:.0%}"
                )
                penalty += 0.20
        except Exception:
            pass

    # ── 8. Experience inflation signal ───────────────────────────────────
    # More than 8 companies in career = suspicious for profiles claiming continuity
    if len(career) >= 9:
        avg_dur = features.get("avg_tenure_months", 24)
        if avg_dur < 10:
            flags.append(
                f"Suspicious job history: {len(career)} roles with avg tenure {avg_dur:.0f} months"
            )
            penalty += 0.15

    honeypot_score = min(penalty, 1.0)
    is_honeypot = honeypot_score >= 0.55

    return {
        "is_honeypot": is_honeypot,
        "honeypot_score": round(honeypot_score, 3),
        "flags": flags,
    }
