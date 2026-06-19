"""
Thin client for Groq's OpenAI-compatible chat completions API.

Used exclusively by the interactive dashboard's Gemini-replaced call sites
(jd_parser.py, llm_scorer.py, clustering.py, interview_gen.py, and the
recruiter chat endpoint in src/api/routes.py). Never imported by
scripts/rank.py or anything it depends on -- that script must remain
network-free per the hackathon's compute constraints regardless of which
hosted LLM provider the interactive demo uses.
"""

import httpx
from src.config import GROQ_API_KEY

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def generate_content(prompt: str, system_instruction: str | None = None, model: str = "llama-3.3-70b-versatile") -> str:
    """Returns the model's text response. Raises on HTTP/network failure so
    callers' existing try/except fallback logic is triggered unchanged."""
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    resp = httpx.post(
        _GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.3},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
