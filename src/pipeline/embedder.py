import hashlib
import numpy as np
import faiss
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from src.config import EMBEDDING_MODEL, FAISS_TOP_K, OUTPUT_DIR

_model: SentenceTransformer | None = None
_ranking_active = False

CACHE_DIR = OUTPUT_DIR / "embedding_cache"
CACHE_DIR.mkdir(exist_ok=True)

# How many candidates pass the TF-IDF pre-filter before dense embedding
PREFILTER_K = 1000


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[Embedder] Loading model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def prefilter_tfidf(jd_text: str, profile_texts: list[str], k: int = PREFILTER_K) -> list[int]:
    """Fast lexical pre-filter: returns indices of top-k candidates by TF-IDF cosine similarity."""
    print(f"[Embedder] TF-IDF pre-filtering {len(profile_texts):,} → top {k}...")
    corpus = [jd_text] + profile_texts
    vec = TfidfVectorizer(
        max_features=20_000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        strip_accents="unicode",
        min_df=2,
    )
    tfidf = vec.fit_transform(corpus)
    jd_vec = tfidf[0]
    cand_vecs = tfidf[1:]
    scores = cosine_similarity(jd_vec, cand_vecs)[0]
    top_indices = np.argsort(scores)[::-1][:k].tolist()
    print(f"[Embedder] Pre-filter done. Top TF-IDF score: {scores[top_indices[0]]:.4f}")
    return top_indices


def build_index(
    profile_texts: list[str],
    jd_text: str = "",
) -> tuple[faiss.Index, np.ndarray, list[int]]:
    """
    Returns (index, embeddings, original_indices).
    original_indices maps position-in-index → position-in-profile_texts.
    """
    # Stage 1: TF-IDF pre-filter
    if len(profile_texts) > PREFILTER_K and jd_text:
        selected_indices = prefilter_tfidf(jd_text, profile_texts, PREFILTER_K)
    else:
        selected_indices = list(range(len(profile_texts)))

    selected_texts = [profile_texts[i] for i in selected_indices]

    # Stage 2: Dense embedding of pre-filtered set only
    cache_key = hashlib.md5(
        (EMBEDDING_MODEL + "".join(selected_texts[:50])).encode()
    ).hexdigest()
    cache_path = CACHE_DIR / f"{cache_key}_{len(selected_texts)}.npy"

    if cache_path.exists():
        print(f"[Embedder] Loading cached embeddings ({len(selected_texts):,} vectors)...")
        embeddings = np.load(str(cache_path))
    else:
        model = get_model()
        print(f"[Embedder] Encoding {len(selected_texts):,} pre-filtered profiles...")
        embeddings = model.encode(
            selected_texts,
            batch_size=256,
            normalize_embeddings=True,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        embeddings = embeddings.astype("float32")
        np.save(str(cache_path), embeddings)
        print(f"[Embedder] Embeddings cached.")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    print(f"[Embedder] FAISS index built: {index.ntotal:,} vectors, dim={dim}")
    return index, embeddings, selected_indices


def search_top_k(
    jd_text: str,
    index: faiss.Index,
    k: int = FAISS_TOP_K,
) -> tuple[np.ndarray, np.ndarray]:
    model = get_model()
    k = min(k, index.ntotal)
    jd_vec = model.encode([jd_text], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
    scores, indices = index.search(jd_vec, k)
    return scores[0], indices[0]


def embed_single(text: str) -> np.ndarray:
    model = get_model()
    return model.encode([text], normalize_embeddings=True, convert_to_numpy=True)[0].astype("float32")


def acquire_rank_lock() -> bool:
    global _ranking_active
    if _ranking_active:
        return False
    _ranking_active = True
    return True


def release_rank_lock():
    global _ranking_active
    _ranking_active = False
