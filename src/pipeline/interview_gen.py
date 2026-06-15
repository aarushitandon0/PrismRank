import json
import re
import google.generativeai as genai
from pathlib import Path
from src.config import GEMINI_API_KEY, MODEL_NAME, OUTPUT_DIR

genai.configure(api_key=GEMINI_API_KEY)


def generate_interview_pack(candidate: dict, jd_parsed: dict) -> dict:
    f = candidate.get("features", {})
    name = f.get("name", "Candidate")
    cid = f.get("candidate_id", "")
    title = f.get("current_title", "N/A")
    top_skills = f.get("top_skills", [])
    assessment = f.get("skill_assessment_scores", {})
    gap_alert = candidate.get("gap_alert") or "none identified"
    standout = candidate.get("standout_signal") or "none identified"
    traj_label = candidate.get("trajectory_label", "Unknown")
    culture_signals = jd_parsed.get("culture_signals", [])
    role_domain = jd_parsed.get("industry_domain", "tech")

    if not GEMINI_API_KEY:
        return _fallback_pack(cid, name, top_skills, gap_alert)

    assessment_str = (
        ", ".join(f"{k}: {v:.0f}/100" for k, v in assessment.items())
        if assessment else "no assessments taken"
    )

    prompt = (
        f"Generate exactly 5 interview questions for {name}, a {title} candidate.\n"
        f"Top skills: {', '.join(top_skills)}\n"
        f"Verified assessment scores: {assessment_str}\n"
        f"Gap identified: {gap_alert}\n"
        f"Standout signal: {standout}\n"
        f"Career trajectory: {traj_label}\n"
        f"Role domain: {role_domain}, culture: {', '.join(culture_signals)}\n\n"
        f"Return a JSON array of exactly 5 objects, each with:\n"
        f"  type: one of 'behavioral' | 'technical' | 'culture'\n"
        f"  question: the interview question (specific to this person)\n"
        f"  what_to_listen_for: what a strong answer looks like (1-2 sentences)\n\n"
        f"Distribution: 2 behavioral (STAR format, targeting gap area), "
        f"2 technical (on strongest verified skills), 1 culture/values question.\n"
        f"Return ONLY JSON array, no markdown."
    )

    try:
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        questions = json.loads(raw)
        if not isinstance(questions, list):
            raise ValueError("Not a list")
    except Exception as e:
        print(f"[Interview Gen] Failed for {name} ({e}), using fallback.")
        return _fallback_pack(cid, name, top_skills, gap_alert)

    return {
        "candidate_id": cid,
        "candidate_name": name,
        "questions": questions[:5],
    }


def _fallback_pack(cid: str, name: str, skills: list, gap: str) -> dict:
    return {
        "candidate_id": cid,
        "candidate_name": name,
        "questions": [
            {
                "type": "behavioral",
                "question": f"Tell me about a time you faced a major technical challenge. How did you resolve it?",
                "what_to_listen_for": "Structured thinking, ownership, outcome-focused narrative.",
            },
            {
                "type": "behavioral",
                "question": f"Describe a situation where you had to work with an ambiguous requirement. What did you do?",
                "what_to_listen_for": "Proactive clarification, stakeholder management, adaptability.",
            },
            {
                "type": "technical",
                "question": f"Walk me through how you would design a system using {skills[0] if skills else 'your primary skill'}.",
                "what_to_listen_for": "Depth of technical knowledge, architectural thinking, trade-off awareness.",
            },
            {
                "type": "technical",
                "question": f"What is your experience with {skills[1] if len(skills) > 1 else 'your secondary skill'}? Give a specific example.",
                "what_to_listen_for": "Practical application, specific projects, measurable impact.",
            },
            {
                "type": "culture",
                "question": "How do you stay current with rapidly changing technology? What have you learned in the last 6 months?",
                "what_to_listen_for": "Learning velocity, curiosity, self-direction, concrete recent examples.",
            },
        ],
    }


def generate_all_packs(shortlist: list[dict], jd_parsed: dict) -> list[dict]:
    packs = []
    top_20 = shortlist[:20]
    quota_exhausted = False
    for i, candidate in enumerate(top_20):
        name = candidate.get("features", {}).get("name", f"Candidate {i+1}")
        print(f"[Interview Gen] Generating pack for {name} ({i+1}/{len(top_20)})...")
        if quota_exhausted:
            packs.append(_fallback_pack(
                candidate.get("features", {}).get("candidate_id", ""),
                name,
                candidate.get("features", {}).get("top_skills", []),
                candidate.get("gap_alert") or "",
            ))
            continue
        try:
            pack = generate_interview_pack(candidate, jd_parsed)
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                print(f"[Interview Gen] Quota exhausted — switching all remaining to fallback.")
                quota_exhausted = True
            pack = _fallback_pack(
                candidate.get("features", {}).get("candidate_id", ""),
                name,
                candidate.get("features", {}).get("top_skills", []),
                candidate.get("gap_alert") or "",
            )
        packs.append(pack)

    out_path = OUTPUT_DIR / "interview_pack.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(packs, f, indent=2, ensure_ascii=False)
    print(f"[Interview Gen] Saved {len(packs)} packs to {out_path}")
    return packs
