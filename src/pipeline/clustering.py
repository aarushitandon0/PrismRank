import numpy as np
from sklearn.cluster import KMeans
from src.config import NUM_CLUSTERS


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

        name, description, strength, gap = _generate_archetype(cluster_id)

        clusters_out.append({
            "id": cluster_id,
            "name": name,
            "description": description,
            "strength": strength,
            "gap": gap,
            "candidates": candidate_ids,
        })

    return {"clusters": clusters_out}


def _generate_archetype(cluster_id: int) -> tuple[str, str, str, str]:
    """Deterministic, local cluster labeling. No network call, no generative
    model -- the name is always a plain numbered label."""
    return (
        f"Cluster {cluster_id + 1}",
        "A group of candidates with similar profile embeddings.",
        "Diverse skill set.",
        "Varied experience.",
    )
