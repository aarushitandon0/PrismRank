FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential curl libgomp1 && rm -rf /var/lib/apt/lists/*

# CPU-only PyTorch to avoid ~2GB GPU packages
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-bake the embedding model so container startup is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"

COPY . .

RUN mkdir -p /app/output /app/data

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
