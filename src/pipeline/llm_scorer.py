import json
import re
from src.config import GROQ_API_KEY, MODEL_NAME
from src.llm_client import generate_content

_SYSTEM = (
    "You are a senior hiring manager at a Series A AI-native company (Redrob AI) evaluating "
    "candidates for a Senior AI Engineer role on the founding team. "
    "The role requires: production embeddings/retrieval experience, vector database knowledge, "
    "strong Python, and hands-on ranking eval (NDCG/MRR). "
    "EXPLICIT DISQUALIFIERS — score these very low on skill_alignment or experience_fit:\n"
    "  - Candidates whose ENTIRE career is at consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini)\n"
    "  - Non-technical titles (Marketing Manager, Accountant, HR) claiming AI/ML skills — this is a keyword trap\n"
    "  - Pure research background without production deployment\n"
    "  - CV/Speech/Robotics specialists without NLP/IR background\n"
    "  - 'AI experience' that is only recent LangChain tutorials\n"
    "BOOSTS — score these higher:\n"
    "  - Production experience shipping ranking/retrieval/recommendation to real users\n"
    "  - Background at product companies (not pure services)\n"
    "  - India-based candidates (Pune/Noida/Bangalore/Hyderabad/Delhi)\n"
    "  - Active platform presence (recently logged in, responsive to recruiters)\n"
    "Focus on genuine fit based on career HISTORY, not keyword matching in skills section. "
    "When skill_assessment_scores are present, treat those as verified ground truth over self-reported skills."
)


def _build_candidate_summary(c: dict) -> str:
    f = c.get("features", {})
    name = f.get("name", "Unknown")
    title = f.get("current_title", "N/A")
    yoe = f.get("years_experience", 0)
    top_skills = f.get("top_skills", [])
    assessment = f.get("skill_assessment_scores", {})
    tier = f.get("education_tier_score", 1)
    traj = c.get("trajectory", {})
    traj_label = traj.get("trajectory_label", "Unknown") if traj else "Unknown"

    career = f.get("career_history", [])
    career_summary = " → ".join(
        f"{r.get('title','')} @ {r.get('company','')}" for r in career[:3]
    )

    assessment_str = (
        ", ".join(f"{k}:{v:.0f}" for k, v in assessment.items())
        if assessment else "none"
    )

    return (
        f"Name: {name} | Title: {title} | YoE: {yoe} | "
        f"Top skills: {', '.join(top_skills)} | "
        f"Verified assessment scores: {assessment_str} | "
        f"Education tier: {tier}/4 | "
        f"Career: {career_summary} | Trajectory: {traj_label}"
    )


def _parse_llm_batch(raw_text: str, batch: list[dict]) -> list[dict]:
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        results = json.loads(text)
        if not isinstance(results, list):
            raise ValueError("Expected JSON array")
        return results
    except Exception:
        # Return safe fallbacks for every candidate in batch
        return [
            {
                "candidate_id": c.get("features", {}).get("candidate_id", ""),
                "skill_alignment": 0.5,
                "experience_fit": 0.5,
                "culture_fit": 0.5,
                "one_line_summary": "Candidate evaluated via rule-based fallback.",
                "gap_alert": None,
                "standout_signal": None,
            }
            for c in batch
        ]


def llm_rerank(jd_parsed: dict, top_candidates: list[dict]) -> list[dict]:
    if not GROQ_API_KEY:
        print("[LLM Scorer] No API key — using fallback scores.")
        for c in top_candidates:
            c["llm"] = {
                "skill_alignment": 0.5,
                "experience_fit": 0.5,
                "culture_fit": 0.5,
                "one_line_summary": "Scored via rule-based pipeline.",
                "gap_alert": None,
                "standout_signal": None,
            }
        return top_candidates

    jd_context = (
        f"Role requires: Hard skills: {', '.join(jd_parsed.get('hard_skills', [])[:10])}. "
        f"Seniority: {jd_parsed.get('seniority_level','mid')} "
        f"({jd_parsed.get('seniority_years_min',3)}+ yrs). "
        f"Culture: {', '.join(jd_parsed.get('culture_signals', []))}. "
        f"Deal-breakers: {', '.join(jd_parsed.get('deal_breakers', []) or ['none'])}. "
        f"Domain: {jd_parsed.get('industry_domain','tech')}."
    )

    llm_map: dict[str, dict] = {}

    batch_size = 10
    for i in range(0, len(top_candidates), batch_size):
        batch = top_candidates[i : i + batch_size]
        summaries = "\n".join(
            f"{j+1}. {_build_candidate_summary(c)}"
            for j, c in enumerate(batch)
        )

        prompt = (
            f"Job context: {jd_context}\n\n"
            f"Evaluate these {len(batch)} candidates and return a JSON array with one object per "
            f"candidate in the SAME ORDER. Each object must have exactly these keys:\n"
            f"  candidate_id (string), skill_alignment (0.0-1.0), experience_fit (0.0-1.0), "
            f"  culture_fit (0.0-1.0), one_line_summary (≤20 words), "
            f"  gap_alert (string or null), standout_signal (string or null)\n\n"
            f"Return ONLY the JSON array, no markdown.\n\n"
            f"Candidates:\n{summaries}"
        )

        try:
            raw_text = generate_content(prompt, system_instruction=_SYSTEM, model=MODEL_NAME)
            results = _parse_llm_batch(raw_text, batch)
        except Exception as e:
            print(f"[LLM Scorer] Batch {i//batch_size+1} failed ({e}), using fallback.")
            results = _parse_llm_batch("", batch)

        for j, res in enumerate(results):
            if j < len(batch):
                cid = batch[j].get("features", {}).get("candidate_id", "")
                if not res.get("candidate_id"):
                    res["candidate_id"] = cid
                llm_map[cid] = res

        print(f"[LLM Scorer] Batch {i//batch_size+1}/{(len(top_candidates)+batch_size-1)//batch_size} done.")

    for c in top_candidates:
        cid = c.get("features", {}).get("candidate_id", "")
        c["llm"] = llm_map.get(cid, {
            "candidate_id": cid,
            "skill_alignment": 0.5,
            "experience_fit": 0.5,
            "culture_fit": 0.5,
            "one_line_summary": "Evaluated via rule-based fallback.",
            "gap_alert": None,
            "standout_signal": None,
        })

    return top_candidates
