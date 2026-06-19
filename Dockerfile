# ── Stage 1: Build React frontend ─────────────────────────────────────────────
FROM node:20-slim AS frontend

WORKDIR /app
COPY ui/package*.json ./ui/
RUN cd ui && npm ci

COPY ui/ ./ui/
RUN cd ui && npm run build
# vite.config.js outDir is '../src/frontend/dist', so output lands at /app/src/frontend/dist


# ── Stage 2: Python backend ────────────────────────────────────────────────────
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only PyTorch (~600MB instead of ~2.5GB for CUDA)
RUN pip install --no-cache-dir \
    torch==2.2.2 torchvision==0.17.2 \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-bake the embedding model so the first request doesn't wait for a download
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy source
COPY src/ ./src/

# Copy built frontend from stage 1
COPY --from=frontend /app/src/frontend/dist/ ./src/frontend/dist/

# Writable runtime directories (data + output need write access)
RUN mkdir -p /app/data /app/output

# HF Spaces Docker requires port 7860.
# PORT env var is respected if set (Railway / Render inject it automatically).
EXPOSE 7860
CMD ["sh", "-c", "python -m uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
