#!/usr/bin/env python3
"""
Standalone CLI runner for PrismRank.
Produces output/submission.csv, output/interview_pack.json, output/bias_report.json.

Usage:
  python scripts/run_pipeline.py rank \
      --jd data/job_description.txt \
      --candidates data/candidates.jsonl \
      --out output/submission.csv
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure src is on the path when run from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import OUTPUT_DIR, FINAL_SHORTLIST, FAISS_TOP_K
from src.pipeline.jd_parser import parse_jd
from src.pipeline.candidate_processor import process_all_candidates, build_candidate_profile
from src.pipeline.embedder import build_index, search_top_k
from src.pipeline.behavioral import score_behavioral
from src.pipeline.trajectory import score_trajectory
from src.pipeline.honeypot import detect_honeypot
from src.pipeline.llm_scorer import llm_rerank
from src.pipeline.fusion import compute_final_score, rank_all
from src.pipeline.clustering import cluster_personas
from src.pipeline.bias_audit import run_bias_audit
from src.pipeline.interview_gen import generate_all_packs


def run(args):
    t0 = time.time()

    # Load JD
    jd_path = Path(args.jd)
    if jd_path.exists():
        jd_text = jd_path.read_text(encoding="utf-8").strip()
        if not jd_text or "Paste or replace" in jd_text:
            print("⚠  data/job_description.txt appears empty — using placeholder JD.")
            jd_text = (
                "Senior ML Engineer role in a fast-growing AI/ML team. "
                "5+ years experience. Strong Python, ML frameworks, and data engineering skills required."
            )
    else:
        print(f"⚠  JD file not found: {jd_path}. Using placeholder.")
        jd_text = (
            "Senior ML Engineer. 5+ years. Python, ML, data engineering required."
        )

    print(f"\n{'='*60}")
    print("  PrismRank — See every dimension of talent.")
    print(f"{'='*60}\n")

    # 1. Parse JD
    print("[1/8] Parsing job description with Gemini Flash...")
    jd_parsed = parse_jd(jd_text)
    print(f"      Detected: {jd_parsed.get('seniority_level')} | {jd_parsed.get('industry_domain')}")
    print(f"      Hard skills: {jd_parsed.get('hard_skills', [])[:6]}")

    # 2. Load candidates
    candidates_path = Path(args.candidates)
    if not candidates_path.exists():
        # Try sample_candidates.json for quick testing
        sample = Path("data/sample_candidates.json")
        if sample.exists():
            print(f"[2/8] {candidates_path} not found, using {sample} for testing.")
            with open(sample, "r", encoding="utf-8") as f:
                raw_list = json.load(f)
            if isinstance(raw_list, list):
                all_profiles = [build_candidate_profile(r) for r in raw_list]
            else:
                all_profiles = [build_candidate_profile(raw_list)]
        else:
            print(f"ERROR: Candidates file not found: {candidates_path}")
            sys.exit(1)
    else:
        print(f"[2/8] Loading candidates from {candidates_path}...")
        all_profiles = process_all_candidates(str(candidates_path))

    print(f"      {len(all_profiles):,} candidates loaded in {time.time()-t0:.1f}s")

    # 3. Build FAISS index
    print("[3/8] Building semantic index...")
    t_emb = time.time()
    profile_texts = [p["profile_text"] for p in all_profiles]
    index, all_embeddings = build_index(profile_texts)
    print(f"      Index built in {time.time()-t_emb:.1f}s")

    # 4. FAISS search
    print(f"[4/8] Searching top-{FAISS_TOP_K} candidates...")
    jd_query = jd_text + " " + " ".join(jd_parsed.get("hard_skills", []))
    scores, indices = search_top_k(jd_query, index, FAISS_TOP_K)
    top_candidates = [all_profiles[int(i)] for i in indices]
    print(f"      Retrieved {len(top_candidates)} candidates for LLM evaluation.")

    # 5. Behavioral + trajectory + honeypot detection
    print("[5/8] Scoring behavioral signals, career trajectories, and honeypot detection...")
    hp_flagged = 0
    for c in top_candidates:
        c["behavioral_score"] = score_behavioral(c["features"])
        c["trajectory"] = score_trajectory(c["features"])
        c["honeypot"] = detect_honeypot(c["features"])
        if c["honeypot"]["is_honeypot"]:
            hp_flagged += 1
    print(f"      {hp_flagged}/{len(top_candidates)} candidates flagged as likely traps (will be down-scored).")

    # 6. LLM re-rank
    print("[6/8] LLM re-ranking (Gemini Flash)...")
    top_candidates = llm_rerank(jd_parsed, top_candidates)

    # 7. Fusion + rank
    print("[7/8] Fusion scoring and final ranking...")
    scored = [compute_final_score(c, jd_parsed) for c in top_candidates]
    ranked_df = rank_all(scored)
    top100_df = ranked_df.head(FINAL_SHORTLIST).copy()

    # 8. Cluster + bias + interview packs
    print("[8/8] Clustering, bias audit, and interview packs...")
    top100_candidates = scored[:FINAL_SHORTLIST]
    top_indices = [int(i) for i in indices[:len(top_candidates)]]
    top100_embeddings = all_embeddings[[top_indices[i] for i in range(min(FINAL_SHORTLIST, len(top_indices)))]]

    personas = cluster_personas(top100_candidates, top100_embeddings)
    bias_report = run_bias_audit(ranked_df)
    generate_all_packs(top100_candidates, jd_parsed)

    # Save outputs
    out_path = Path(args.out)
    out_path.parent.mkdir(exist_ok=True)
    submission_df = top100_df[["candidate_id", "rank", "final_score", "reasoning"]].copy()
    submission_df.columns = ["candidate_id", "rank", "score", "reasoning"]
    submission_df.to_csv(out_path, index=False)

    bias_path = OUTPUT_DIR / "bias_report.json"
    with open(bias_path, "w") as f:
        json.dump(bias_report, f, indent=2)

    elapsed = round(time.time() - t0, 1)

    print(f"\n{'='*60}")
    print(f"  ✅ Pipeline complete in {elapsed}s")
    print(f"  📄 submission.csv  → {out_path}")
    print(f"  📋 interview_pack.json → {OUTPUT_DIR / 'interview_pack.json'}")
    print(f"  🔍 bias_report.json → {bias_path}")
    print(f"  Top 3 candidates:")
    for _, row in top100_df.head(3).iterrows():
        print(f"    #{int(row['rank'])}  {row['name']} — {row['final_score']:.4f} ({row['tier']})")
    if not bias_report["audit_passed"]:
        print(f"\n  ⚠  Bias warnings: {len(bias_report['warnings'])}")
        for w in bias_report["warnings"][:2]:
            print(f"     • {w}")
    print(f"{'='*60}\n")

    return 0


def main():
    parser = argparse.ArgumentParser(description="PrismRank pipeline runner")
    subparsers = parser.add_subparsers(dest="command")

    rank_parser = subparsers.add_parser("rank", help="Run the ranking pipeline")
    rank_parser.add_argument("--jd", default="data/job_description.txt", help="Path to job description text file")
    rank_parser.add_argument("--candidates", default="data/candidates.jsonl", help="Path to candidates JSONL file")
    rank_parser.add_argument("--out", default="output/submission.csv", help="Output path for submission CSV")

    args = parser.parse_args()

    if args.command == "rank":
        sys.exit(run(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
