def score_behavioral(features: dict) -> float:
    redrob = features.get("redrob", {})
    score = 0.0

    conn = redrob.get("connection_count", 0) or 0
    if conn > 500:
        score += 0.08
    elif conn > 200:
        score += 0.04

    end = redrob.get("endorsements_received", 0) or 0
    if end > 20:
        score += 0.10
    elif end > 5:
        score += 0.05

    rr = redrob.get("recruiter_response_rate", 0) or 0
    if rr > 0.8:
        score += 0.12
    elif rr > 0.5:
        score += 0.06

    icr = redrob.get("interview_completion_rate", 0) or 0
    if icr > 0.8:
        score += 0.12
    elif icr > 0.5:
        score += 0.06

    oar = redrob.get("offer_acceptance_rate", -1)
    if isinstance(oar, (int, float)) and oar != -1 and oar > 0.7:
        score += 0.10

    completeness = redrob.get("profile_completeness_score", 0) or 0
    if completeness > 90:
        score += 0.10
    elif completeness > 70:
        score += 0.05

    github = redrob.get("github_activity_score", -1)
    if isinstance(github, (int, float)) and github != -1:
        if github > 70:
            score += 0.12
        elif github > 40:
            score += 0.06

    saved = redrob.get("saved_by_recruiters_30d", 0) or 0
    if saved > 10:
        score += 0.08
    elif saved > 3:
        score += 0.04

    assessment_scores = redrob.get("skill_assessment_scores") or {}
    if assessment_scores:
        score += 0.08
        high_count = sum(1 for v in assessment_scores.values() if isinstance(v, (int, float)) and v > 80)
        score += min(high_count * 0.01, 0.02)

    if redrob.get("verified_email") and redrob.get("verified_phone"):
        score += 0.06

    if redrob.get("linkedin_connected"):
        score += 0.04

    if redrob.get("open_to_work_flag"):
        score += 0.05

    return min(score, 1.0)
