import json
from pathlib import Path

_EDU_TIER_MAP = {"tier_1": 4, "tier_2": 3, "tier_3": 2, "tier_4": 1}
_PROF_WEIGHT = {"advanced": 3, "intermediate": 2, "beginner": 1}


def _build_profile_text(raw: dict) -> str:
    profile = raw.get("profile", {})
    parts = []

    for field in ("headline", "summary", "current_title"):
        if profile.get(field):
            parts.append(profile[field])

    for role in raw.get("career_history", []):
        for field in ("title", "company", "description"):
            if role.get(field):
                parts.append(role[field])

    skill_names = [s["name"] for s in raw.get("skills", []) if s.get("name")]
    if skill_names:
        parts.append(" ".join(skill_names))

    for edu in raw.get("education", []):
        for field in ("field_of_study", "degree", "institution"):
            if edu.get(field):
                parts.append(edu[field])

    for cert in raw.get("certifications", []):
        if cert.get("name"):
            parts.append(cert["name"])

    return " ".join(parts)


def _extract_features(raw: dict) -> dict:
    profile = raw.get("profile", {})
    career = raw.get("career_history", [])
    skills_raw = raw.get("skills", [])
    education = raw.get("education", [])
    redrob = raw.get("redrob_signals", {})

    # Sort skills by endorsements + proficiency weight to pick top-10
    sorted_skills = sorted(
        skills_raw,
        key=lambda s: s.get("endorsements", 0) + _PROF_WEIGHT.get(s.get("proficiency", ""), 1) * 5,
        reverse=True,
    )
    top_skills = [s["name"] for s in sorted_skills[:10]]
    skills_list = [s["name"] for s in skills_raw]

    # Highest education tier seen
    edu_tier = 1
    for edu in education:
        edu_tier = max(edu_tier, _EDU_TIER_MAP.get(edu.get("tier", ""), 1))

    # Average tenure across all roles
    durations = [r["duration_months"] for r in career if r.get("duration_months")]
    avg_tenure = round(sum(durations) / len(durations), 1) if durations else 24.0

    return {
        "candidate_id": raw.get("candidate_id", ""),
        "name": profile.get("anonymized_name", ""),
        "current_title": profile.get("current_title", ""),
        "current_company": profile.get("current_company", ""),
        "location": profile.get("location", ""),
        "country": profile.get("country", ""),
        "years_experience": profile.get("years_of_experience", 0),
        "top_skills": top_skills,
        "skills_list": skills_list,
        "skill_assessment_scores": redrob.get("skill_assessment_scores", {}),
        "education_tier_score": edu_tier,
        "education": education,
        "career_history": career,
        "avg_tenure_months": avg_tenure,
        "open_to_work": bool(redrob.get("open_to_work_flag", False)),
        "redrob": redrob,
    }


def process_all_candidates(candidates_path: str) -> list[dict]:
    path = Path(candidates_path)
    candidates = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue

            candidates.append({
                "candidate_id": raw.get("candidate_id", ""),
                "profile_text": _build_profile_text(raw),
                "features": _extract_features(raw),
            })

    print(f"[CandidateProcessor] Loaded {len(candidates):,} candidates from {path.name}")
    return candidates
