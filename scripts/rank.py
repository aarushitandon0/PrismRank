#!/usr/bin/env python3
"""
Compliant ranking entrypoint for the Redrob Hackathon v4 submission.

Produces the required top-100 ranked candidate CSV. Makes zero network calls
and imports zero LLM SDKs anywhere in its call graph (verified against every
module it touches: candidate_processor, embedder, behavioral, trajectory,
honeypot, jd_local, local_scorer, fusion). Runs entirely on CPU.

This script is what gets reproduced at Stage 3 inside the sandboxed Docker
container. The interactive FastAPI/React dashboard (src/api, ui/) optionally
uses Gemini for JD parsing nuance, persona naming, interview question
generation, and recruiter chat -- none of that is used here, and none of it
produces the scored submission.

One-time setup, run once before the timed ranking step (see scripts/precompute.py
for the full pre-computation pass -- this is the allowance the spec makes for
"pre-computation may exceed the 5-minute window, but the ranking step that
produces the CSV must complete within it"):
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
    python scripts/precompute.py --candidates data/candidates.jsonl --jd data/job_description.txt

Usage (the timed step, completes in well under 5 minutes with warm caches):
    python scripts/rank.py --candidates data/candidates.jsonl --out submission.csv
"""

import argparse
import sys
import time

# Reproduction environments are not guaranteed to default to a UTF-8 console
# (e.g. Windows cp1252). Reconfigure stdout/stderr defensively so a stray
# non-ASCII character in a log line can never crash the ranking step.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from src.config import FINAL_SHORTLIST, FAISS_TOP_K
from src.pipeline.candidate_processor import process_all_candidates
from src.pipeline.embedder import build_index, search_top_k
from src.pipeline.behavioral import score_behavioral
from src.pipeline.trajectory import score_trajectory
from src.pipeline.honeypot import detect_honeypot
from src.pipeline.jd_local import parse_jd_local
from src.pipeline.local_scorer import attach_local_llm_proxy, generate_reasoning
from src.pipeline.fusion import compute_final_score, rank_all
from src.pipeline.precompute_cache import get_or_build_candidates, get_or_build_tfidf

PREFILTER_K = 1000

HONEYPOT_HARD_CUTOFF = 0.55
DEFAULT_JD_TEXT = (
    "Senior AI Engineer, Founding Team, Redrob AI. 5-9 years experience. "
    "Embeddings, vector databases, Python, ranking evaluation frameworks (NDCG, MRR) required. "
    "Consulting-only careers and non-technical titles claiming AI skills are disqualified."
)


def run(candidates_path: Path, jd_path: Path, out_path: Path) -> int:
    t0 = time.time()

    jd_text = jd_path.read_text(encoding="utf-8").strip() if jd_path.exists() else DEFAULT_JD_TEXT
    jd_parsed = parse_jd_local(jd_text)
    print(f"[1/6] JD parsed locally, no network call. Hard skills: {jd_parsed['hard_skills'][:6]}")

    all_profiles = get_or_build_candidates(candidates_path, process_all_candidates)
    print(f"[2/6] Loaded {len(all_profiles):,} candidates (cached) in {time.time() - t0:.1f}s")

    profile_texts = [p["profile_text"] for p in all_profiles]
    jd_query = jd_text + " " + " ".join(jd_parsed.get("hard_skills", []))

    vectorizer, tfidf_matrix = get_or_build_tfidf(candidates_path, profile_texts)
    jd_vec = vectorizer.transform([jd_query])
    sims = cosine_similarity(jd_vec, tfidf_matrix)[0]
    k = min(PREFILTER_K, len(profile_texts))
    top_indices = np.argsort(sims)[::-1][:k].tolist()
    print(f"[3a/6] TF-IDF pre-filter (cached vectorizer) -> top {k} in {time.time() - t0:.1f}s")

    index, all_embeddings, original_indices = build_index(
        profile_texts, jd_query, preselected_indices=top_indices
    )
    print(f"[3b/6] FAISS index built over {len(original_indices):,} pre-filtered candidates in {time.time() - t0:.1f}s")

    scores, local_indices = search_top_k(jd_query, index, FAISS_TOP_K)
    pool = []
    for score, li in zip(scores, local_indices):
        c = all_profiles[original_indices[int(li)]]
        c["_cosine_score"] = float(max(0.0, min(1.0, score)))
        pool.append(c)
    print(f"[4/6] Retrieved top {len(pool)} candidates by semantic similarity in {time.time() - t0:.1f}s")

    for c in pool:
        c["behavioral_score"] = score_behavioral(c["features"])
        c["trajectory"] = score_trajectory(c["features"])
        c["honeypot"] = detect_honeypot(c["features"])
        attach_local_llm_proxy(c, jd_parsed, c["_cosine_score"])

    scored = [compute_final_score(c, jd_parsed) for c in pool]
    hp_count = sum(1 for c in scored if c["honeypot_score"] >= HONEYPOT_HARD_CUTOFF)
    print(f"[5/6] Scored {len(scored)} candidates in {time.time() - t0:.1f}s. {hp_count} flagged as honeypots and excluded.")

    clean = [c for c in scored if c["honeypot_score"] < HONEYPOT_HARD_CUTOFF]
    if len(clean) < FINAL_SHORTLIST:
        flagged = sorted(
            (c for c in scored if c["honeypot_score"] >= HONEYPOT_HARD_CUTOFF),
            key=lambda c: c["honeypot_score"],
        )
        clean += flagged[: FINAL_SHORTLIST - len(clean)]

    ranked_df = rank_all(clean)
    top100_df = ranked_df.head(FINAL_SHORTLIST).copy()

    score_lookup = {c["candidate_id"]: c for c in clean}
    reasonings = []
    for _, row in top100_df.iterrows():
        c = score_lookup[row["candidate_id"]]
        reasonings.append(generate_reasoning(c, jd_parsed, int(row["rank"])))
    top100_df["reasoning"] = reasonings

    submission_df = top100_df[["candidate_id", "rank", "final_score", "reasoning"]].copy()
    submission_df.columns = ["candidate_id", "rank", "score", "reasoning"]
    submission_df["score"] = submission_df["score"].round(4)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    submission_df.to_csv(out_path, index=False, encoding="utf-8")

    elapsed = round(time.time() - t0, 1)
    print(f"[6/6] Wrote {len(submission_df)} rows to {out_path} in {elapsed}s total.")
    if elapsed > 280:
        print("WARNING: runtime is approaching the 5-minute compute budget.")
    print(f"Top 3: " + ", ".join(
        f"#{int(r['rank'])} {r['candidate_id']} ({r['score']:.3f})"
        for _, r in submission_df.head(3).iterrows()
    ))
    return 0


def main():
    parser = argparse.ArgumentParser(description="PrismRank compliant ranking script")
    parser.add_argument("--candidates", default="data/candidates.jsonl", help="Path to candidates JSONL file")
    parser.add_argument("--jd", default="data/job_description.txt", help="Path to job description text file")
    parser.add_argument("--out", default="submission.csv", help="Output path for the ranked CSV")
    args = parser.parse_args()

    sys.exit(run(Path(args.candidates), Path(args.jd), Path(args.out)))


if __name__ == "__main__":
    main()
