from src.config import SENIORITY_MAP, COMPANY_SIZE_MAP


def _infer_seniority(title: str) -> int:
    title_lower = title.lower()
    best = 0
    for keyword, level in SENIORITY_MAP.items():
        if keyword in title_lower:
            best = max(best, level)
    return best


def score_trajectory(features: dict) -> dict:
    career = features.get("career_history", [])
    yoe = float(features.get("years_experience", 1) or 1)

    # --- Velocity: seniority climb over career ---
    seniority_levels = [_infer_seniority(r.get("title", "")) for r in career]
    if len(seniority_levels) >= 2:
        starting = seniority_levels[-1]   # oldest role last in typical ordering
        peak = max(seniority_levels)
        climb = peak - starting
        velocity_score = min(climb / max(yoe, 1) / 0.5, 1.0)
    elif len(seniority_levels) == 1:
        velocity_score = min(seniority_levels[0] / 4.0, 1.0)
    else:
        velocity_score = 0.3

    # --- Tier progression: company size of last 2 roles ---
    sizes = []
    for role in career[:2]:
        sz = role.get("company_size", "")
        sizes.append(COMPANY_SIZE_MAP.get(sz, 1))

    if len(sizes) >= 2:
        if sizes[0] >= sizes[1]:
            tier_progression = 0.8 + min((sizes[0] - sizes[1]) * 0.05, 0.2)
        else:
            tier_progression = max(0.3, 0.5 - (sizes[1] - sizes[0]) * 0.05)
    elif len(sizes) == 1:
        tier_progression = 0.5
    else:
        tier_progression = 0.5

    tier_progression = min(tier_progression, 1.0)

    # --- Tenure: avg months per role ---
    avg_tenure = features.get("avg_tenure_months", 24)
    if avg_tenure < 12:
        tenure_score = 0.2
    elif avg_tenure <= 24:
        tenure_score = 0.2 + (avg_tenure - 12) / 12 * 0.4
    elif avg_tenure <= 48:
        tenure_score = 1.0
    elif avg_tenure <= 72:
        tenure_score = 1.0 - (avg_tenure - 48) / 24 * 0.4
    else:
        tenure_score = 0.6

    # --- Composite ---
    composite = velocity_score * 0.4 + tier_progression * 0.3 + tenure_score * 0.3
    trajectory_percentile = round(composite * 100, 1)

    # --- Label ---
    if velocity_score > 0.7 and trajectory_percentile > 70:
        label = "Rocket"
    elif trajectory_percentile > 60:
        label = "Steady Climber"
    elif velocity_score < 0.3 and tenure_score > 0.7:
        label = "Veteran"
    elif yoe < 3:
        label = "Early Stage"
    else:
        label = "Lateral Mover"

    return {
        "velocity_score": round(velocity_score, 3),
        "tier_progression": round(tier_progression, 3),
        "tenure_score": round(tenure_score, 3),
        "trajectory_percentile": trajectory_percentile,
        "trajectory_label": label,
    }
