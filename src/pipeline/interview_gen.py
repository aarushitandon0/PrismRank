import json
from pathlib import Path
from src.config import OUTPUT_DIR


def generate_interview_pack(candidate: dict, jd_parsed: dict) -> dict:
    """Deterministic, template-based interview pack. No network call, no
    generative model -- questions are filled in from the candidate's actual
    top skills and gap alert."""
    f = candidate.get("features", {})
    name = f.get("name", "Candidate")
    cid = f.get("candidate_id", "")
    top_skills = f.get("top_skills", [])
    gap_alert = candidate.get("gap_alert") or "none identified"
    return _fallback_pack(cid, name, top_skills, gap_alert)


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
    for i, candidate in enumerate(top_20):
        name = candidate.get("features", {}).get("name", f"Candidate {i+1}")
        print(f"[Interview Gen] Generating pack for {name} ({i+1}/{len(top_20)})...")
        pack = generate_interview_pack(candidate, jd_parsed)
        packs.append(pack)

    out_path = OUTPUT_DIR / "interview_pack.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(packs, f, indent=2, ensure_ascii=False)
    print(f"[Interview Gen] Saved {len(packs)} packs to {out_path}")
    return packs
