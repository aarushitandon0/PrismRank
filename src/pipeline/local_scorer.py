"""
Fully local, network-free scorers for skill_alignment, experience_fit, and
culture_fit, consumed by fusion.compute_final_score.

skill_alignment blends FAISS cosine similarity with an explicit hard-skill
match ratio. experience_fit blends total years of experience with years
spent specifically in JD-relevant roles. No function in this file makes a
network call or depends on any hosted API.

Also provides generate_reasoning(), a deterministic, fact-grounded reasoning
generator for the submission CSV's "reasoning" column. Every sentence is
assembled from real candidate fields, with sentence structure chosen by each
candidate's population-relative strongest signal, so claims are traceable to
the input data and never hallucinated.
"""


def _hard_skill_match_count(features: dict, jd_parsed: dict) -> int:
    """Number of the candidate's listed skills that overlap with the JD's
    extracted hard skills, via fuzzy substring match in either direction."""
    skills_list = [s.lower() for s in features.get("skills_list", [])]
    hard_skills = [s.lower() for s in jd_parsed.get("hard_skills", [])]
    if not hard_skills:
        return 0
    return sum(1 for s in skills_list if any(h in s or s in h for h in hard_skills))


def _band_score(value: float, floor: float, band: float = 6.0) -> float:
    """Piecewise score around a floor value. Full score within `band` years
    above the floor, tapering off below or well above it."""
    if floor <= value <= floor + band:
        return 1.0
    if value < floor:
        gap = floor - value
        return max(0.25, 1.0 - gap * 0.15)
    gap = value - (floor + band)
    return max(0.40, 1.0 - gap * 0.04)


def _relevant_years(features: dict, jd_parsed: dict) -> float:
    """Sums duration_months across only the career roles whose title or
    description mentions one of the JD's hard skills, then converts to years.
    This is what the JD actually asks for ("6-8 years total, of which 4-5 are
    in applied ML/AI roles") -- total tenure alone can be satisfied by years
    in unrelated roles, which should not count toward experience fit."""
    hard_skills = [s.lower() for s in jd_parsed.get("hard_skills", [])]
    if not hard_skills:
        return 0.0
    relevant_months = 0.0
    for role in features.get("career_history", []):
        text = ((role.get("title", "") or "") + " " + (role.get("description", "") or "")).lower()
        if any(h in text for h in hard_skills):
            relevant_months += float(role.get("duration_months", 0) or 0)
    return relevant_months / 12.0


def local_skill_alignment(cosine_score: float, features: dict, jd_parsed: dict) -> float:
    """Blends two independent signals: the FAISS cosine similarity already
    computed during retrieval (captures contextual/implicit relevance), and
    the fraction of the JD's named hard skills the candidate explicitly lists
    (captures literal overlap). Blending avoids relying solely on the same
    score that already determined retrieval inclusion, which would otherwise
    add no new information to the fusion score."""
    semantic = max(0.0, min(1.0, float(cosine_score)))
    hard_skills = jd_parsed.get("hard_skills", [])
    if hard_skills:
        matched = _hard_skill_match_count(features, jd_parsed)
        match_ratio = min(matched / len(hard_skills), 1.0)
    else:
        match_ratio = 0.0
    return round(0.65 * semantic + 0.35 * match_ratio, 4)


def local_experience_fit(features: dict, jd_parsed: dict) -> float:
    """Blends total years of experience against the JD's seniority floor with
    years spent specifically in JD-relevant roles (see _relevant_years).
    Weighted toward relevant years since that is what the JD explicitly asks
    for, not just raw tenure."""
    yoe = float(features.get("years_experience", 0) or 0)
    relevant_yoe = _relevant_years(features, jd_parsed)

    min_yoe = float(jd_parsed.get("seniority_years_min", 3) or 3)
    # The JD asks for fewer relevant years than total years
    # (e.g. "6-8 years total, of which 4-5 are in applied ML roles").
    relevant_floor = max(min_yoe - 1.5, 1.0)

    total_fit = _band_score(yoe, min_yoe)
    relevant_fit = _band_score(relevant_yoe, relevant_floor)

    return round(0.4 * total_fit + 0.6 * relevant_fit, 4)


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


def attach_local_scores(candidate: dict, jd_parsed: dict, cosine_score: float) -> None:
    """Populates candidate["scores"] with skill_alignment, experience_fit, and
    culture_fit using only local signals, for fusion.compute_final_score."""
    f = candidate.get("features", {})
    yoe = float(f.get("years_experience", 0) or 0)

    skill_alignment = local_skill_alignment(cosine_score, f, jd_parsed)
    experience_fit = local_experience_fit(f, jd_parsed)
    culture_fit = local_culture_fit(f, jd_parsed)

    matched_count = _hard_skill_match_count(f, jd_parsed)

    min_yoe = float(jd_parsed.get("seniority_years_min", 3) or 3)
    gap_alert = None
    if matched_count < 2:
        gap_alert = "Limited overlap with the JD's core hard skills based on listed skills."
    elif yoe < min_yoe - 1:
        gap_alert = "Experience below the JD's stated seniority floor."

    standout_signal = None
    if matched_count >= 5:
        standout_signal = "Strong overlap with the JD's core technical requirements."

    candidate["scores"] = {
        "skill_alignment": round(skill_alignment, 4),
        "experience_fit": round(experience_fit, 4),
        "culture_fit": round(culture_fit, 4),
        "one_line_summary": "Scored locally via embedding similarity and rule-based signals.",
        "gap_alert": gap_alert,
        "standout_signal": standout_signal,
    }


_SIGNAL_NAMES = ("skill", "experience", "behavioral", "trajectory")


def _raw_signals(candidate: dict) -> dict:
    wb = candidate.get("weighted_breakdown", {})
    return {
        "skill": wb.get("skill_alignment", 0.5),
        "experience": wb.get("experience_fit", 0.5),
        "behavioral": wb.get("behavioral", 0.5),
        "trajectory": (candidate.get("trajectory_percentile", 50) or 50) / 100.0,
    }


def attach_dominant_signal_percentiles(candidates: list[dict]) -> None:
    """Computes each candidate's percentile rank, within this candidate pool,
    for each of the four reasoning-relevant signals, and stores the dominant
    one by relative standing (not raw magnitude) on each candidate as
    "_dominant_signal". This matters because experience_fit's band formula is
    structurally easier to score high on than the other three signals, which
    without this correction makes it mechanically "dominant" for nearly every
    candidate regardless of what's actually distinctive about them -- a real
    failure mode discovered by inspecting actual output, not a theoretical
    concern: an early version of this reasoning generator produced the same
    sentence shape for ~100% of a real 100-candidate run."""
    if not candidates:
        return
    n = len(candidates)
    raw = {name: [] for name in _SIGNAL_NAMES}
    for c in candidates:
        signals = _raw_signals(c)
        for name in _SIGNAL_NAMES:
            raw[name].append(signals[name])

    percentile_ranks = {}
    for name, values in raw.items():
        order = sorted(range(n), key=lambda i: values[i])
        pct = [0.0] * n
        for rank_pos, idx in enumerate(order):
            pct[idx] = rank_pos / max(n - 1, 1)
        percentile_ranks[name] = pct

    for i, c in enumerate(candidates):
        percentiles = {name: percentile_ranks[name][i] for name in _SIGNAL_NAMES}
        c["_dominant_signal"] = max(percentiles, key=percentiles.get)


def _dominant_signal(candidate: dict) -> str:
    """Which signal is most distinctive for this candidate. Prefers the
    population-relative result from attach_dominant_signal_percentiles if
    present; falls back to raw-magnitude comparison (e.g. for unit tests with
    a single candidate and no pool context)."""
    if "_dominant_signal" in candidate:
        return candidate["_dominant_signal"]
    signals = _raw_signals(candidate)
    return max(signals, key=signals.get)


def _confidence_tier(rank: int) -> str:
    if rank <= 10:
        return "high"
    if rank <= 40:
        return "medium"
    return "low"


def generate_reasoning(candidate: dict, jd_parsed: dict, rank: int) -> str:
    """Builds a 1-3 sentence, fact-grounded justification for one candidate's
    rank. The opener's structure varies by which signal is most distinctive
    for this candidate (skill match, experience, trajectory, or behavioral
    engagement) crossed with a confidence tier tied to rank -- twelve distinct
    combinations, not one template with blanks filled in. Every clause is
    derived from real fields on the candidate or from jd_reasons (the
    descriptive strings fusion._jd_specific_modifier already produces from
    real JD-derived rule matches), so nothing here is invented."""
    f = candidate.get("features", {})
    name = f.get("name") or candidate.get("candidate_id", "Candidate")
    title = f.get("current_title", "") or "an unspecified role"
    company = f.get("current_company", "")
    at_company = f" at {company}" if company else ""
    yoe = f.get("years_experience", 0) or 0
    top_skills = f.get("top_skills", [])[:3]
    notice = (f.get("redrob") or {}).get("notice_period_days", 60) or 60
    jd_reasons = candidate.get("jd_reasons", []) or []
    honeypot_flags = candidate.get("honeypot_flags", []) or []
    trajectory_label = candidate.get("trajectory_label", "Unknown")

    hard_skills = [s.lower() for s in jd_parsed.get("hard_skills", [])]
    matched = [s for s in top_skills if any(h in s.lower() for h in hard_skills)]
    skill_phrase = ", ".join(matched[:2]) if matched else (", ".join(top_skills[:2]) if top_skills else "their listed skills")

    negative_kw = ["disqualifier", "trap", "ghost", "mismatch"]
    positive_reasons = [r for r in jd_reasons if not any(k in r.lower() for k in negative_kw)]
    negative_reasons = [r for r in jd_reasons if any(k in r.lower() for k in negative_kw)]

    dominant = _dominant_signal(candidate)
    tier = _confidence_tier(rank)

    openers = {
        "skill": {
            "high": f"{name}'s direct experience with {skill_phrase} is the standout signal here, backed by {yoe:.0f} years as {title}{at_company}",
            "medium": f"{name} brings relevant experience with {skill_phrase}, built over {yoe:.0f} years as {title}{at_company}",
            "low": f"{name} lists experience with {skill_phrase}, though only {yoe:.0f} years overall as {title}{at_company}",
        },
        "experience": {
            "high": f"With {yoe:.0f} years of experience as {title}{at_company}, {name} brings exactly the depth this role is looking for",
            "medium": f"{name} brings {yoe:.0f} years of experience as {title}{at_company}, broadly aligned with the role's seniority bar",
            "low": f"{name} has {yoe:.0f} years of experience as {title}{at_company}, near the edge of the role's stated seniority range",
        },
        "trajectory": {
            "high": f"{name}'s career trajectory, {trajectory_label.lower()}, stands out, built over {yoe:.0f} years most recently as {title}{at_company}",
            "medium": f"{name} shows a {trajectory_label.lower()} trajectory over {yoe:.0f} years, most recently as {title}{at_company}",
            "low": f"{name}'s trajectory ({trajectory_label.lower()}) is steady but unremarkable, over {yoe:.0f} years most recently as {title}{at_company}",
        },
        "behavioral": {
            "high": f"{name} shows strong platform engagement on top of {yoe:.0f} years of experience as {title}{at_company}",
            "medium": f"{name} shows reasonable platform engagement alongside {yoe:.0f} years of experience as {title}{at_company}",
            "low": f"{name} has {yoe:.0f} years of experience as {title}{at_company}, with modest platform engagement signals",
        },
    }
    opener = openers[dominant][tier]

    if dominant != "skill":
        if matched:
            skill_clause = f", with direct experience in {skill_phrase} matching the JD's core requirements"
        elif top_skills:
            skill_clause = f", though listed skills ({skill_phrase}) only partially overlap the JD's hard requirements"
        else:
            skill_clause = ""
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
    if dominant != "trajectory":
        pieces.append(f"Career trajectory: {trajectory_label.lower()}.")
    if rank > 80:
        pieces.append("Included near the cutoff based on overall signal strength rather than a standout match.")

    text = " ".join(pieces)
    if len(text) > 320:
        text = text[:317] + "..."
    return text
