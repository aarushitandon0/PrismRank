import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME: str = "gemini-2.0-flash"
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

FAISS_TOP_K: int = 200
FINAL_SHORTLIST: int = 100
NUM_CLUSTERS: int = 5

SCORE_WEIGHTS: dict = {
    "skill_match": 0.30,
    "experience_fit": 0.25,
    "behavioral": 0.20,
    "redrob_signals": 0.15,
    "culture_soft": 0.10,
}

SENIORITY_MAP: dict = {
    "intern": 0,
    "trainee": 0,
    "junior": 1,
    "associate": 1,
    "entry": 1,
    "mid": 2,
    "senior": 3,
    "sr": 3,
    "lead": 4,
    "tech lead": 4,
    "staff": 5,
    "principal": 6,
    "director": 7,
    "vp": 8,
    "vice president": 8,
    "cto": 9,
    "ceo": 9,
    "head": 6,
}

EDUCATION_TIER_MAP: dict = {
    "tier_1": 4,
    "tier_2": 3,
    "tier_3": 2,
    "tier_4": 1,
    "unknown": 1,
}

PROFICIENCY_MAP: dict = {
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
    "expert": 4,
}

COMPANY_SIZE_MAP: dict = {
    "1-10": 1,
    "11-50": 2,
    "51-200": 3,
    "201-500": 4,
    "501-1000": 5,
    "1001-5000": 6,
    "5001-10000": 7,
    "10001+": 8,
}

BASE_DIR: Path = Path(__file__).parent.parent
DATA_DIR: Path = BASE_DIR / "data"
OUTPUT_DIR: Path = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
