"""
Fully local, network-free substitutes for the Gemini-derived skill_alignment,
experience_fit, and culture_fit signals consumed by fusion.compute_final_score.

This module exists so scripts/rank.py (the compliant ranking entrypoint) can
populate the exact same candidate["llm"] shape the interactive, Gemini-enabled
pipeline produces, allowing fusion.compute_final_score, the JD-specific
multipliers, and honeypot suppression to run completely unchanged. No function
in this file makes a network call or imports an LLM SDK.

Also provides generate_reasoning(), a deterministic, fact-grounded reasoning
generator for the submission CSV's "reasoning" column. Every sentence is built
from real candidate fields and real JD-derived multiplier reasons, so claims
are traceable to the input data and never hallucinated.
"""


def local_skill_alignment(cosine_score: float) -> float:
    """Cosine similarity between the candidate's profile embedding and the JD
    query embedding, already computed during FAISS retrieval. Clamped to [0,1]."""
    return max(0.0, min(1.0, float(cosine_score)))


def local_experience_fit(yoe: float, jd_parsed: dict) -> float:
    """Piecewise score around the JD's stated seniority floor. Full score within
    a 6-year band above the floor, tapering off below or well above it."""
    min_yoe = float(jd_parsed.get("seniority_years_min", 3) or 3)
    band = 6.0
    if min_yoe <= yoe <= min_yoe + band:
        return 1.0
    if yoe < min_yoe:
        gap = min_yoe - yoe
        return max(0.25, 1.0 - gap * 0.15)
    gap = yoe - (min_yoe + band)
    return max(0.40, 1.0 - gap * 0.04)


def local_culture_fit(features: dict, jd_parsed: dict) -> float:
    """Keyword overlap between the candidate's role titles/descriptions and the
    JD's extracted culture signals. Intentionally narrow: the heavier JD-specific
    business rules (consulting penalty, product company boost, etc.) already live
    in fusion._jd_specific_modifier and are applied separately as a multiplier."""
    career = features.get("career_history", [])
    text = " ".join(
        (r.get("title", "") + " " + r.get("description", "")) for r in career
    ).lower()
    culture_signals = jd_parsed.get("culture_signals", [])
    matches = sum(1 for sig in culture_signals if sig.lower() in text)
    score = 0.45 + min(matches * 0.08, 0.35)
    return max(0.0, min(1.0, score))


def attach_local_llm_proxy(candidate: dict, jd_parsed: dict, cosine_score: float) -> None:
    """Populates candidate["llm"] using only local signals. Drop-in replacement
    for src.pipeline.llm_scorer.llm_rerank's per-candidate output shape."""
    f = candidate.get("features", {})
    yoe = float(f.get("years_experience", 0) or 0)

    skill_alignment = local_skill_alignment(cosine_score)
    experience_fit = local_experience_fit(yoe, jd_parsed)
    culture_fit = local_culture_fit(f, jd_parsed)

    skills_list = [s.lower() for s in f.get("skills_list", [])]
    hard_skills = [s.lower() for s in jd_parsed.get("hard_skills", [])]
    matched_count = sum(1 for s in skills_list if any(h in s for h in hard_skills))

    min_yoe = float(jd_parsed.get("seniority_years_min", 3) or 3)
    gap_alert = None
    if matched_count < 2:
        gap_alert = "Limited overlap with the JD's core hard skills based on listed skills."
    elif yoe < min_yoe - 1:
        gap_alert = "Experience below the JD's stated seniority floor."

    standout_signal = None
    if matched_count >= 5:
        standout_signal = "Strong overlap with the JD's core technical requirements."

    candidate["llm"] = {
        "skill_alignment": round(skill_alignment, 4),
        "experience_fit": round(experience_fit, 4),
        "culture_fit": round(culture_fit, 4),
        "one_line_summary": "Scored locally via embedding similarity and rule-based signals.",
        "gap_alert": gap_alert,
        "standout_signal": standout_signal,
    }


def generate_reasoning(candidate: dict, jd_parsed: dict, rank: int) -> str:
    """Builds a 1-3 sentence, fact-grounded justification for one candidate's
    rank. Every clause is derived from real fields on the candidate or from
    jd_reasons (the descriptive strings fusion._jd_specific_modifier already
    produces from real JD-derived rule matches), so nothing here is invented."""
    f = candidate.get("features", {})
    name = f.get("name") or candidate.get("candidate_id", "Candidate")
    title = f.get("current_title", "") or "an unspecified role"
    company = f.get("current_company", "")
    yoe = f.get("years_experience", 0) or 0
    top_skills = f.get("top_skills", [])[:3]
    notice = (f.get("redrob") or {}).get("notice_period_days", 60) or 60
    jd_reasons = candidate.get("jd_reasons", []) or []
    honeypot_flags = candidate.get("honeypot_flags", []) or []
    trajectory_label = candidate.get("trajectory_label", "Unknown")

    hard_skills = [s.lower() for s in jd_parsed.get("hard_skills", [])]
    matched = [s for s in top_skills if any(h in s.lower() for h in hard_skills)]

    negative_kw = ["disqualifier", "trap", "ghost", "mismatch"]
    positive_reasons = [r for r in jd_reasons if not any(k in r.lower() for k in negative_kw)]
    negative_reasons = [r for r in jd_reasons if any(k in r.lower() for k in negative_kw)]

    if rank <= 10:
        opener = f"{name}, {title}" + (f" at {company}" if company else "") + f" with {yoe:.0f} years of experience, is a strong fit for the role"
    elif rank <= 40:
        opener = f"{name}, {title} with {yoe:.0f} years of experience, is a solid match for the role"
    else:
        opener = f"{name}, {title} with {yoe:.0f} years of experience, meets baseline requirements"

    if matched:
        skill_clause = f", with direct experience in {', '.join(matched[:2])} matching the JD's core requirements"
    elif top_skills:
        skill_clause = f", though listed skills ({', '.join(top_skills[:2])}) only partially overlap the JD's hard requirements"
    else:
        skill_clause = ""

    concerns = []
    if notice > 60:
        concerns.append(f"a {int(notice)}-day notice period")
    if negative_reasons:
        concerns.append(negative_reasons[0].lower())
    if honeypot_flags:
        concerns.append("minor profile inconsistencies flagged by automated checks")

    pieces = [opener + skill_clause + "."]
    if positive_reasons:
        pieces.append(positive_reasons[0] + ".")
    if concerns:
        pieces.append("Concern: " + "; ".join(concerns) + ".")
    pieces.append(f"Career trajectory: {trajectory_label.lower()}.")
    if rank > 80:
        pieces.append("Included near the cutoff based on overall signal strength rather than a standout match.")

    text = " ".join(pieces)
    if len(text) > 320:
        text = text[:317] + "..."
    return text
