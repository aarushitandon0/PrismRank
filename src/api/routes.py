import asyncio
import json
import shutil
import time
import numpy as np
import pandas as pd
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse

from src.api.schemas import (
    RankRequest, RankResponse, ChatQuery, ChatResponse,
    CandidateCard, StatusResponse,
)
from src.config import OUTPUT_DIR, FINAL_SHORTLIST, FAISS_TOP_K, MODEL_NAME, GROQ_API_KEY
from src.llm_client import generate_content

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _np_clean(obj):
    """Recursively convert all numpy scalars/arrays to plain Python types."""
    if isinstance(obj, dict):
        return {k: _np_clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_np_clean(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, float) and np.isnan(obj):
        return None
    return obj


def _safe(val, typ, default):
    try:
        v = val if not callable(getattr(val, 'item', None)) else val.item()
        return typ(v) if v is not None and not (isinstance(v, float) and np.isnan(v)) else default
    except Exception:
        return default

def _df_row_to_card(row: pd.Series, rank: int | None = None) -> CandidateCard:
    r = int(rank) if rank is not None else _safe(row.get("rank", 0), int, 0)
    skills = row.get("top_skills", [])
    if not isinstance(skills, list):
        skills = []
    return CandidateCard(
        rank=r,
        candidate_id=str(row.get("candidate_id", "") or ""),
        name=str(row.get("name", "") or ""),
        final_score=_safe(row.get("final_score", 0), float, 0.0),
        tier=str(row.get("tier", "C") or "C"),
        skill_alignment=_safe(row.get("skill_alignment", 0.5), float, 0.5),
        experience_fit=_safe(row.get("experience_fit", 0.5), float, 0.5),
        behavioral_score=_safe(row.get("behavioral_score", 0.0), float, 0.0),
        culture_fit=_safe(row.get("culture_fit", 0.5), float, 0.5),
        one_line_summary=str(row.get("one_line_summary", "") or ""),
        gap_alert=str(row["gap_alert"]) if pd.notna(row.get("gap_alert")) else None,
        standout_signal=str(row["standout_signal"]) if pd.notna(row.get("standout_signal")) else None,
        trajectory_label=str(row.get("trajectory_label", "Unknown") or "Unknown"),
        top_skills=[str(s) for s in skills],
        reasoning=str(row.get("reasoning", "") or ""),
        years_experience=_safe(row.get("years_experience", 0), float, 0.0),
        current_title=str(row.get("current_title", "") or ""),
        current_company=str(row.get("current_company", "") or ""),
        location=str(row.get("location", "") or ""),
        country=str(row.get("country", "") or ""),
        open_to_work=bool(_safe(row.get("open_to_work", False), int, 0)),
        preferred_work_mode=str(row.get("preferred_work_mode", "any") or "any"),
        willing_to_relocate=bool(_safe(row.get("willing_to_relocate", False), int, 0)),
        notice_period_days=_safe(row.get("notice_period_days", 60) or 60, int, 60),
        exceptional_fit=bool(_safe(row.get("exceptional_fit", False), int, 0)),
        cluster_id=int(row["cluster_id"]) if pd.notna(row.get("cluster_id")) else None,
    )


async def _run_in_thread(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/api/upload-candidates")
async def upload_candidates(file: UploadFile = File(...)):
    from src.config import DATA_DIR
    DATA_DIR.mkdir(exist_ok=True)
    if not file.filename.endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="Only .jsonl files are accepted.")
    dest = DATA_DIR / "candidates.jsonl"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    size_mb = round(dest.stat().st_size / 1_048_576, 1)
    return {"ok": True, "path": "data/candidates.jsonl", "size_mb": size_mb}


@router.post("/api/reset-lock")
async def reset_lock():
    from src.pipeline.embedder import release_rank_lock
    try:
        release_rank_lock()
    except Exception:
        pass
    return {"ok": True, "message": "Lock released."}


@router.get("/api/status", response_model=StatusResponse)
async def status(request=None):
    from fastapi import Request
    from src.api.main import app
    loaded = 0
    try:
        from src.api import main as m
        loaded = getattr(m.app.state, "candidates_loaded", 0)
    except Exception:
        pass
    return StatusResponse(status="ready", model=MODEL_NAME, candidates_loaded=loaded)


@router.post("/api/rank", response_model=RankResponse)
async def rank_candidates(req: RankRequest):
    from src.api.main import app
    from src.pipeline.candidate_processor import process_all_candidates
    from src.pipeline.embedder import build_index, search_top_k
    from src.pipeline.jd_parser import parse_jd
    from src.pipeline.behavioral import score_behavioral
    from src.pipeline.trajectory import score_trajectory
    from src.pipeline.honeypot import detect_honeypot
    from src.pipeline.llm_scorer import llm_rerank
    from src.pipeline.fusion import compute_final_score, rank_all
    from src.pipeline.clustering import cluster_personas
    from src.pipeline.bias_audit import run_bias_audit
    from src.pipeline.interview_gen import generate_all_packs

    from src.pipeline.embedder import acquire_rank_lock, release_rank_lock
    if not acquire_rank_lock():
        raise HTTPException(status_code=429, detail="A ranking job is already running. Please wait.")

    t0 = time.time()

    candidates_path = Path(req.candidates_path)
    if not candidates_path.exists():
        release_rank_lock()
        raise HTTPException(status_code=404, detail=f"Candidates file not found: {candidates_path}")

    try:
        # 1. Parse JD
        print("[Routes] Parsing JD...")
        jd_parsed = await _run_in_thread(parse_jd, req.jd_text)
        app.state.jd_parsed = jd_parsed

        # 2. Load + process candidates
        print("[Routes] Processing candidates...")
        all_profiles = await _run_in_thread(process_all_candidates, str(candidates_path))
        app.state.candidates_loaded = len(all_profiles)

        # 3. Build FAISS index (TF-IDF pre-filter → dense embed top-1000 only)
        print("[Routes] Building FAISS index...")
        profile_texts = [p["profile_text"] for p in all_profiles]

        jd_query = (
            req.jd_text + " " +
            " ".join(jd_parsed.get("hard_skills", [])) + " " +
            " ".join(jd_parsed.get("soft_skills", []))
        )

        index, all_embeddings, original_indices = await _run_in_thread(
            build_index, profile_texts, jd_query
        )

        # 4. FAISS retrieval: top-200 within the pre-filtered set
        print("[Routes] Searching top candidates...")
        scores, local_indices = await _run_in_thread(search_top_k, jd_query, index, FAISS_TOP_K)

        # Map local FAISS indices back to global candidate list
        top_candidates = [all_profiles[original_indices[int(i)]] for i in local_indices]

        # 5. Behavioral + trajectory scoring for top-200
        print("[Routes] Scoring behavioral + trajectory...")
        def score_all(candidates):
            hp_count = 0
            for c in candidates:
                c["behavioral_score"] = score_behavioral(c["features"])
                c["trajectory"] = score_trajectory(c["features"])
                c["honeypot"] = detect_honeypot(c["features"])
                if c["honeypot"]["is_honeypot"]:
                    hp_count += 1
            print(f"[Routes] Honeypot detector: {hp_count}/{len(candidates)} flagged as likely traps.")
            return candidates

        top_candidates = await _run_in_thread(score_all, top_candidates)

        # 6. LLM re-rank
        print("[Routes] LLM re-ranking...")
        top_candidates = await _run_in_thread(llm_rerank, jd_parsed, top_candidates)

        # 7. Fusion scoring
        print("[Routes] Fusion scoring...")
        def fuse_all(candidates):
            return [compute_final_score(c, jd_parsed) for c in candidates]

        top_candidates = await _run_in_thread(fuse_all, top_candidates)

        # 8. Rank all, take top-100
        ranked_df = await _run_in_thread(rank_all, top_candidates)
        top100_df = ranked_df.head(FINAL_SHORTLIST).copy()

        # 9. Cluster top-100
        print("[Routes] Clustering personas...")
        top100_embeddings = all_embeddings[[int(i) for i in local_indices[:FINAL_SHORTLIST]]]
        top100_candidates = top_candidates[:FINAL_SHORTLIST]

        personas = await _run_in_thread(cluster_personas, top100_candidates, top100_embeddings)
        app.state.personas = personas

        # Attach cluster_id to df rows
        cid_to_cluster = {}
        for cluster in personas.get("clusters", []):
            for cid in cluster.get("candidates", []):
                cid_to_cluster[cid] = cluster["id"]

        top100_df["cluster_id"] = top100_df["candidate_id"].map(cid_to_cluster)

        # 10. Bias audit
        print("[Routes] Running bias audit...")
        bias_report = await _run_in_thread(run_bias_audit, ranked_df)
        app.state.bias_report = bias_report

        # 11. Interview packs for top-20
        print("[Routes] Generating interview packs...")
        await _run_in_thread(generate_all_packs, top100_candidates, jd_parsed)

        # 12. Save submission.csv
        submission_path = OUTPUT_DIR / "submission.csv"
        submission_df = top100_df[["candidate_id", "rank", "final_score", "reasoning"]].copy()
        submission_df.columns = ["candidate_id", "rank", "score", "reasoning"]
        submission_df.to_csv(submission_path, index=False)
        print(f"[Routes] submission.csv saved → {submission_path}")

        # 13. Save bias report
        bias_path = OUTPUT_DIR / "bias_report.json"
        with open(bias_path, "w") as fh:
            json.dump(_np_clean(bias_report), fh, indent=2)

        app.state.ranked_df = top100_df

        elapsed = round(time.time() - t0, 1)
        print(f"[Routes] Pipeline complete in {elapsed}s")

        shortlist = [_df_row_to_card(row) for _, row in top100_df.iterrows()]

        payload = _np_clean({
            "shortlist": [c.model_dump() for c in shortlist],
            "personas": personas,
            "bias_report": bias_report,
            "total_candidates": len(all_profiles),
            "processing_time_seconds": elapsed,
        })
        return JSONResponse(content=payload)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[Routes] Pipeline error: {type(e).__name__}: {e}")
        print(tb)
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}" or type(e).__name__)
    finally:
        release_rank_lock()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatQuery):
    from src.api.main import app

    ranked_df = getattr(app.state, "ranked_df", None)
    jd_parsed = getattr(app.state, "jd_parsed", {})

    if ranked_df is None or ranked_df.empty:
        return ChatResponse(
            query=req.query,
            results=[],
            filter_applied="No ranking has been run yet. Please run /api/rank first.",
        )

    # Use Groq to parse the query into filter criteria
    filter_desc = req.query
    filtered = ranked_df.copy()

    if GROQ_API_KEY:
        try:
            parse_prompt = (
                f"Parse this recruiter query into filter criteria JSON:\n"
                f"Query: \"{req.query}\"\n\n"
                f"Return JSON with optional keys:\n"
                f"  skill_keywords: list of skill names to match\n"
                f"  min_score: float 0-1\n"
                f"  min_years: int\n"
                f"  max_years: int\n"
                f"  seniority: string (junior/mid/senior)\n"
                f"  work_mode: string (remote/hybrid/onsite/flexible)\n"
                f"  open_to_work: bool\n"
                f"  tier: string (A/B/C)\n"
                f"  trajectory_label: string\n"
                f"Return ONLY JSON, no markdown."
            )
            raw = generate_content(parse_prompt, model=MODEL_NAME).strip()
            raw = __import__("re").sub(r"^```(?:json)?\s*", "", raw)
            raw = __import__("re").sub(r"\s*```$", "", raw)
            criteria = json.loads(raw)
        except Exception:
            criteria = {}
    else:
        criteria = _rule_based_parse(req.query)

    # Apply filters
    filters_used = []

    if criteria.get("min_score"):
        filtered = filtered[filtered["final_score"] >= float(criteria["min_score"])]
        filters_used.append(f"score≥{criteria['min_score']}")

    if criteria.get("min_years"):
        filtered = filtered[filtered["years_experience"] >= float(criteria["min_years"])]
        filters_used.append(f"exp≥{criteria['min_years']}yr")

    if criteria.get("max_years"):
        filtered = filtered[filtered["years_experience"] <= float(criteria["max_years"])]
        filters_used.append(f"exp≤{criteria['max_years']}yr")

    if criteria.get("open_to_work"):
        filtered = filtered[filtered["open_to_work"] == True]
        filters_used.append("open_to_work")

    if criteria.get("tier"):
        filtered = filtered[filtered["tier"] == criteria["tier"].upper()]
        filters_used.append(f"tier={criteria['tier'].upper()}")

    if criteria.get("work_mode"):
        wm = criteria["work_mode"].lower()
        filtered = filtered[filtered["preferred_work_mode"].str.lower() == wm]
        filters_used.append(f"mode={wm}")

    if criteria.get("trajectory_label"):
        tl = criteria["trajectory_label"].lower()
        filtered = filtered[filtered["trajectory_label"].str.lower().str.contains(tl)]
        filters_used.append(f"trajectory={tl}")

    if criteria.get("skill_keywords"):
        def has_skill(row):
            skills = row.get("top_skills", [])
            if isinstance(skills, list):
                skills_lower = [s.lower() for s in skills]
                return any(
                    kw.lower() in " ".join(skills_lower)
                    for kw in criteria["skill_keywords"]
                )
            return False
        mask = filtered.apply(has_skill, axis=1)
        filtered = filtered[mask]
        filters_used.append(f"skills={criteria['skill_keywords']}")

    filtered = filtered.sort_values("final_score", ascending=False).head(req.top_k)

    if filtered.empty:
        filter_desc_str = ", ".join(filters_used) if filters_used else "none"
        return ChatResponse(
            query=req.query,
            results=[],
            filter_applied=f"No candidates matched filters: {filter_desc_str}. Try relaxing criteria.",
        )

    results = [_df_row_to_card(row) for _, row in filtered.iterrows()]
    filter_applied = ", ".join(filters_used) if filters_used else "semantic match"

    payload = _np_clean({
        "query": req.query,
        "results": [r.model_dump() for r in results],
        "filter_applied": filter_applied,
    })
    return JSONResponse(content=payload)


def _rule_based_parse(query: str) -> dict:
    import re
    q = query.lower()
    criteria: dict = {}

    yr = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", q)
    if yr:
        criteria["min_years"] = int(yr.group(1))

    if "open" in q or "available" in q or "looking" in q:
        criteria["open_to_work"] = True

    for mode in ["remote", "hybrid", "onsite"]:
        if mode in q:
            criteria["work_mode"] = mode
            break

    for tier in ["a", "b", "c"]:
        if f"tier {tier}" in q or f"tier-{tier}" in q:
            criteria["tier"] = tier.upper()
            break

    for label in ["rocket", "steady climber", "veteran", "early stage", "lateral mover"]:
        if label in q:
            criteria["trajectory_label"] = label
            break

    skills = re.findall(r"\b(python|java|sql|aws|gcp|ml|nlp|react|spark|kafka|docker|kubernetes)\b", q)
    if skills:
        criteria["skill_keywords"] = list(set(skills))

    return criteria


@router.get("/api/personas")
async def get_personas():
    from src.api.main import app
    return getattr(app.state, "personas", {"clusters": []})


@router.get("/api/bias-report")
async def get_bias_report():
    from src.api.main import app
    return getattr(app.state, "bias_report", {})


@router.get("/api/download/submission-csv")
async def download_submission():
    path = OUTPUT_DIR / "submission.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="submission.csv not found. Run /api/rank first.")
    return FileResponse(str(path), filename="submission.csv", media_type="text/csv")


@router.get("/api/download/interview-pack")
async def download_interview_pack():
    path = OUTPUT_DIR / "interview_pack.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="interview_pack.json not found. Run /api/rank first.")
    return FileResponse(str(path), filename="interview_pack.json", media_type="application/json")
