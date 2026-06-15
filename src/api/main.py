from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.api.routes import router

app = FastAPI(title="PrismRank API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# State placeholders
app.state.ranked_df = None
app.state.jd_parsed = {}
app.state.personas = {"clusters": []}
app.state.bias_report = {}
app.state.candidates_loaded = 0

app.include_router(router)

DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"
ASSETS_DIR = DIST_DIR / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index = DIST_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    # fallback to old index during development
    old = Path(__file__).parent.parent / "frontend" / "index.html"
    return HTMLResponse(old.read_text(encoding="utf-8"))


@app.on_event("startup")
async def on_startup():
    print("=" * 60)
    print("  PrismRank is live — See every dimension of talent.")
    print("=" * 60)
    # Pre-load embedding model so first /api/rank is faster
    try:
        from src.pipeline.embedder import get_model
        get_model()
        print("[Startup] Embedding model loaded and ready.")
    except Exception as e:
        print(f"[Startup] Could not pre-load embedding model: {e}")
