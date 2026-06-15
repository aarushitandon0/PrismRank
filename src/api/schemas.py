from pydantic import BaseModel, Field
from typing import Optional, Any


class RankRequest(BaseModel):
    jd_text: str
    candidates_path: str = "data/candidates.jsonl"


class ChatQuery(BaseModel):
    query: str
    top_k: int = 10


class CandidateCard(BaseModel):
    rank: int
    candidate_id: str
    name: str
    final_score: float
    tier: str
    skill_alignment: float
    experience_fit: float
    behavioral_score: float
    culture_fit: float
    one_line_summary: str
    gap_alert: Optional[str] = None
    standout_signal: Optional[str] = None
    trajectory_label: str
    top_skills: list[str]
    reasoning: str
    years_experience: float = 0
    current_title: str = ""
    current_company: str = ""
    location: str = ""
    country: str = ""
    open_to_work: bool = False
    preferred_work_mode: str = "any"
    willing_to_relocate: bool = False
    notice_period_days: int = 60
    exceptional_fit: bool = False
    cluster_id: Optional[int] = None


class RankResponse(BaseModel):
    shortlist: list[CandidateCard]
    personas: dict
    bias_report: dict
    total_candidates: int
    processing_time_seconds: float


class ChatResponse(BaseModel):
    query: str
    results: list[CandidateCard]
    filter_applied: str


class StatusResponse(BaseModel):
    status: str
    model: str
    candidates_loaded: int
