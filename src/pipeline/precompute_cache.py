"""
Disk caches keyed off the candidates file's size and mtime, not its content
hash, so cache checks are instant even on a 465MB file. Used to move expensive,
JD-independent work (JSON parsing, TF-IDF vectorizer fitting) out of the timed
ranking step and into an explicit, documented, untimed pre-computation step
(scripts/precompute.py), per the hackathon's stated allowance for pre-computed
artifacts.
"""

import hashlib
import pickle
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer

from src.config import OUTPUT_DIR

CACHE_DIR = OUTPUT_DIR / "precompute_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _file_key(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.name}:{stat.st_size}:{int(stat.st_mtime)}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def get_or_build_candidates(candidates_path: Path, builder) -> list[dict]:
    """builder: callable(str) -> list[dict], i.e. process_all_candidates."""
    key = _file_key(candidates_path)
    cache_path = CACHE_DIR / f"candidates_{key}.pkl"
    if cache_path.exists():
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    profiles = builder(str(candidates_path))
    with open(cache_path, "wb") as f:
        pickle.dump(profiles, f, protocol=pickle.HIGHEST_PROTOCOL)
    return profiles


def get_or_build_tfidf(candidates_path: Path, profile_texts: list[str]):
    """Returns (vectorizer, matrix). Fitting over 100K documents is the single
    most expensive step in the pipeline (~4 minutes observed); caching it here
    means the timed ranking step only ever does a fast .transform() on the JD."""
    key = _file_key(candidates_path)
    vec_path = CACHE_DIR / f"tfidf_vec_{key}.pkl"
    mat_path = CACHE_DIR / f"tfidf_mat_{key}.npz"
    if vec_path.exists() and mat_path.exists():
        with open(vec_path, "rb") as f:
            vectorizer = pickle.load(f)
        matrix = sp.load_npz(mat_path)
        return vectorizer, matrix

    vectorizer = TfidfVectorizer(
        max_features=20_000,
        ngram_range=(1, 1),
        sublinear_tf=True,
        strip_accents="unicode",
        min_df=2,
        dtype=np.float32,
    )
    matrix = vectorizer.fit_transform(profile_texts)
    with open(vec_path, "wb") as f:
        pickle.dump(vectorizer, f, protocol=pickle.HIGHEST_PROTOCOL)
    sp.save_npz(mat_path, matrix)
    return vectorizer, matrix
