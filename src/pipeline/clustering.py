import json
import re
import numpy as np
import google.generativeai as genai
from sklearn.cluster import KMeans
from src.config import GEMINI_API_KEY, MODEL_NAME, NUM_CLUSTERS

genai.configure(api_key=GEMINI_API_KEY)


def cluster_personas(top_candidates: list[dict], embeddings: np.ndarray) -> dict:
    n = len(top_candidates)
    k = min(NUM_CLUSTERS, n)

    if n < k:
        return {"clusters": []}

    embs = embeddings.astype("float32")
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(embs)

    clusters_raw: dict[int, list] = {i: [] for i in range(k)}
    for idx, label in enumerate(labels):
        clusters_raw[int(label)].append(top_candidates[idx])

    clusters_out = []
    for cluster_id, members in clusters_raw.items():
        candidate_ids = [
            m.get("features", {}).get("candidate_id", "") for m in members
        ]
        sample = members[:3]
        sample_texts = "\n".join(
            f"- {m.get('features',{}).get('name','?')}: "
            f"{m.get('features',{}).get('current_title','?')}, "
            f"{m.get('features',{}).get('years_experience',0)} yrs, "
            f"skills: {', '.join(m.get('features',{}).get('top_skills',[])[:4])}"
            for m in sample
        )

        name, description, strength, gap = _generate_archetype(sample_texts, cluster_id)

        clusters_out.append({
            "id": cluster_id,
            "name": name,
            "description": description,
            "strength": strength,
            "gap": gap,
            "candidates": candidate_ids,
        })

    return {"clusters": clusters_out}


def _generate_archetype(sample_texts: str, cluster_id: int) -> tuple[str, str, str, str]:
    if not GEMINI_API_KEY:
        return (
            f"Cluster {cluster_id + 1}",
            "A group of similar candidates.",
            "Diverse skill set.",
            "Varied experience.",
        )

    try:
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        prompt = (
            f"Here are 3 candidate profiles from a talent cluster:\n{sample_texts}\n\n"
            f"Return a JSON object with exactly these keys:\n"
            f"  name (3-4 word archetype, e.g. 'Deep ML Specialist'),\n"
            f"  description (1 sentence on what unites them),\n"
            f"  strength (their collective strength),\n"
            f"  gap (their collective gap for a typical tech role)\n"
            f"Return ONLY JSON, no markdown."
        )
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        return (
            parsed.get("name", f"Cluster {cluster_id+1}"),
            parsed.get("description", ""),
            parsed.get("strength", ""),
            parsed.get("gap", ""),
        )
    except Exception as e:
        print(f"[Clustering] Archetype gen failed for cluster {cluster_id}: {e}")
        return (
            f"Talent Cluster {cluster_id + 1}",
            "A cohesive group of candidates with shared background.",
            "Consistent domain expertise.",
            "Requires deeper evaluation.",
        )
