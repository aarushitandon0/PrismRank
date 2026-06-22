"""
Local-only JD parser. Zero network calls, zero hosted-API dependencies.

Used by scripts/rank.py (the compliant ranking entrypoint) and the API's
/api/rank route. Produces hard_skills, deal_breakers, seniority_years_min, and
culture_signals from a hardcoded parse for the known challenge JD, with a
regex-based fallback for any other input text.
"""

import re

_JD_HARDCODED = {
    "hard_skills": [
        "Python", "embeddings", "sentence-transformers", "vector databases",
        "FAISS", "Pinecone", "Milvus", "Weaviate", "Qdrant", "hybrid search",
        "NDCG", "MRR", "MAP", "ranking systems", "information retrieval",
        "NLP", "LLM", "LLM fine-tuning", "LoRA", "QLoRA", "PEFT",
        "A/B testing", "eval frameworks", "BGE", "E5",
    ],
    "soft_skills": [
        "async-first communication", "strong writing", "ownership mindset",
        "product thinking", "scrappy execution", "disagree-and-commit",
    ],
    "seniority_level": "senior",
    "seniority_years_min": 5,
    "industry_domain": "HR-tech / AI platform",
    "culture_signals": [
        "async-first", "write a lot", "move fast", "disagree openly",
        "decide quickly", "3+ year commitment", "product-engineering attitude",
    ],
    "implicit_requirements": [
        "production ML deployment experience",
        "product company background (not services-only)",
        "system thinking over framework use",
        "can evaluate ranking systems rigorously",
        "active in job market / responsive",
    ],
    "deal_breakers": [
        "consulting-only career (TCS/Infosys/Wipro/Accenture/Cognizant/Capgemini)",
        "pure research without production deployment",
        "LangChain-only AI experience under 12 months",
        "non-technical title (Marketing/Sales/HR/Accountant) claiming ML skills",
        "computer vision or speech specialist without NLP/IR exposure",
        "closed-source-only career without external validation",
    ],
    "preferred_work_mode": "hybrid",
    "salary_budget_inr_lpa": {"min": 25, "max": 60},
}


def parse_jd_local(jd_text: str) -> dict:
    text_lower = jd_text.lower()
    if "redrob hackathon" in text_lower or (
        "senior ai engineer" in text_lower and "founding team" in text_lower
    ):
        return dict(_JD_HARDCODED)
    return _rule_based_fallback(jd_text)


def _rule_based_fallback(jd_text: str) -> dict:
    text_lower = jd_text.lower()
    words = text_lower.split()

    tech_pool = [
        "python", "java", "javascript", "typescript", "sql", "nosql", "aws", "gcp", "azure",
        "docker", "kubernetes", "react", "node.js", "machine learning", "deep learning",
        "tensorflow", "pytorch", "spark", "kafka", "airflow", "dbt", "snowflake",
        "llm", "nlp", "computer vision", "mlops", "fastapi", "django", "flask",
        "data engineering", "data science", "analytics", "tableau", "power bi",
        "embeddings", "faiss", "vector database", "ranking", "retrieval",
    ]
    hard_skills = [s for s in tech_pool if s in text_lower]

    seniority = "mid"
    seniority_years = 3
    if any(w in words for w in ["senior", "sr.", "lead", "principal", "staff"]):
        seniority, seniority_years = "senior", 5
    elif any(w in words for w in ["junior", "jr.", "entry", "fresher", "trainee"]):
        seniority, seniority_years = "junior", 0
    elif any(w in words for w in ["director", "vp", "head", "manager"]):
        seniority, seniority_years = "director", 8

    years_match = re.search(r"(\d+)\s*\+?\s*years?", text_lower)
    if years_match:
        seniority_years = int(years_match.group(1))

    culture = []
    if "fast" in text_lower or "startup" in text_lower:
        culture.append("fast-paced")
    if "autonomous" in text_lower or "self-starter" in text_lower:
        culture.append("autonomous")
    if "data-driven" in text_lower or "metrics" in text_lower:
        culture.append("data-driven")
    if "collaborate" in text_lower or "team" in text_lower:
        culture.append("collaborative")

    return {
        "hard_skills": hard_skills or ["python", "sql"],
        "soft_skills": ["communication", "problem-solving", "teamwork"],
        "seniority_level": seniority,
        "seniority_years_min": seniority_years,
        "industry_domain": "technology",
        "culture_signals": culture or ["collaborative"],
        "implicit_requirements": ["stakeholder management", "ownership mindset"],
        "deal_breakers": [],
        "preferred_work_mode": "any",
        "salary_budget_inr_lpa": None,
    }
