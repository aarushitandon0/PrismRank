# PrismRank

**AI-native candidate ranking and talent intelligence system.**
Built for the India Runs Data & AI Challenge (Intelligent Candidate Discovery & Ranking by Redrob).

---

## Overview

PrismRank is a full-stack talent intelligence pipeline that ingests 100,000+ candidate profiles, runs a three-stage retrieval and re-ranking system, and surfaces a bias-audited shortlist of the top 100 candidates for a given job description. It ships with a React dashboard, a recruiter chat interface, persona clustering, and automated interview pack generation.

The system was designed around the specific failure modes in the challenge dataset: keyword-stuffed profiles, honeypot candidates with impossibly consistent signals, and consulting-only careers claiming ML expertise. Every scoring component targets at least one of these failure modes explicitly.

---

## Architecture

```
candidates.jsonl (100,000 profiles)
        |
        v
  CandidateProcessor
  - Parses JSONL, builds profile prose for retrieval
  - Extracts structured features for scoring
        |
        v
  Stage 1: TF-IDF Pre-filter
  - TfidfVectorizer (bigram, sublinear TF, 20K vocab)
  - Narrows 100K candidates to top 1,000 by JD cosine similarity
  - Runs in under 1 second on CPU
        |
        v
  Stage 2: FAISS Dense Retrieval
  - all-MiniLM-L6-v2 embeddings (384-dim)
  - Flat L2 index over pre-filtered 1,000 candidates
  - Returns top 200 by semantic similarity to JD query
        |
        v
  Stage 3: Gemini 2.0 Flash Re-ranking
  - Batches of 10 candidates per API call
  - Scores each on: skill_alignment, experience_fit,
    culture_fit, gap_alert, standout_signal
  - Grounds scores in career history, not keyword lists
        |
        v
  Behavioral Scorer       (17 Redrob platform signals)
  Trajectory Scorer       (velocity x tier progression x tenure)
  Honeypot Detector       (7-signal impossibility detection)
        |
        v
  Fusion Scorer
  - Weighted combination of all signals
  - JD-specific multipliers (consulting penalty, title-skill trap,
    India location boost, notice period boost)
  - Honeypot suppression multiplier
        |
        v
  Top-100 Shortlist
        |
        |-- KMeans Clustering (k=5, Gemini-generated archetypes)
        |-- Bias Audit (5 fairness dimensions, Gini + skew ratios)
        |-- Interview Pack Generation (top 20 candidates, 5Q each)
        |-- submission.csv
```

---

## Score Weights

| Signal | Weight | Source |
|---|---|---|
| Skill alignment | 30% | Gemini 2.0 Flash |
| Experience fit | 25% | Gemini 2.0 Flash |
| Behavioral score | 20% | Redrob platform signals |
| Platform signals | 15% | Redrob activity data |
| Culture fit | 10% | Gemini 2.0 Flash |

### JD-Specific Multipliers

| Condition | Multiplier |
|---|---|
| Consulting-only career (TCS/Infosys/Wipro/etc.) | 0.50x |
| Non-technical title claiming 3+ AI skills | 0.45x |
| CV/Speech specialist without NLP/IR background | 0.70x |
| Inactive 180+ days and response rate below 15% | 0.75x |
| India-based candidate | 1.08x |
| Sub-30-day notice period | 1.04x |
| 5+ core JD skill matches | 1.07x |
| Trajectory above 85th percentile | 1.08x |
| Verified assessment scores above 75 on matched skills | 1.05x |

---

## Honeypot Detection

The challenge dataset contains approximately 80 trap candidates with subtly impossible profiles. Any submission with more than 10% honeypots in the top 100 is disqualified. PrismRank detects these via seven independent signals:

1. Temporal impossibility: years of experience vs. graduation date gap
2. Title-skill mismatch: non-technical title with expert-level ML skills
3. Signal saturation: multiple behavioral metrics simultaneously maxed
4. Assessment score suspicion: all scores identical or perfectly consistent
5. Keyword stuffing: AI keywords with no supporting career history
6. Consulting-only career: explicitly disqualified by the JD
7. Activity ghost: inactive for 180+ days with a sub-10% recruiter response rate

---

## Bias Audit

Five fairness dimensions are computed over the shortlist vs. the full candidate pool:

| Dimension | Method | Warning Threshold |
|---|---|---|
| Education tier concentration | Skew ratio (shortlist vs. pool) | Greater than 1.5x |
| Geography concentration | Gini coefficient over country distribution | Greater than 0.6 |
| Experience distribution | Under-3yr exclusion skew | Reported |
| Profile completeness | Average score gap (top 20% vs. pool) | Reported |
| Relocation willingness | Shortlist vs. pool share | Reported |

Results from the competition run: audit_passed = false, with three active warnings: education tier 1 concentration at 2.44x skew, India geography dominance at Gini 0.675, and under-3yr candidate exclusion at 4.6x skew.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| LLM | Gemini 2.0 Flash (google-generativeai) |
| Embeddings | sentence-transformers, all-MiniLM-L6-v2 |
| Vector search | FAISS (IndexFlatL2) |
| Lexical pre-filter | scikit-learn TfidfVectorizer |
| Clustering | scikit-learn KMeans (k=5) |
| Data processing | pandas, numpy |
| Frontend | React 18, Vite, Tailwind CSS |
| Fonts | Fraunces (display), Inter (body), JetBrains Mono (labels) |

---

## Project Structure

```
prismrank/
  data/
    candidates.jsonl          # 100K candidate profiles (not included)
    job_description.txt       # Target JD for the challenge
  src/
    api/
      main.py                 # FastAPI app, static file serving
      routes.py               # /api/rank, /api/chat, /api/status
      schemas.py              # Pydantic models
    pipeline/
      candidate_processor.py  # JSONL parsing, feature extraction
      embedder.py             # TF-IDF pre-filter, FAISS index, embeddings
      jd_parser.py            # JD parsing (Gemini or rule-based fallback)
      llm_scorer.py           # Gemini re-ranking in batches of 10
      behavioral.py           # 17-signal Redrob behavioral scorer
      trajectory.py           # Velocity x tier progression x tenure
      honeypot.py             # 7-signal trap candidate detector
      fusion.py               # Weighted score fusion + JD multipliers
      clustering.py           # KMeans + Gemini archetype generation
      bias_audit.py           # 5-dimension fairness audit
      interview_gen.py        # Interview pack generation
    frontend/
      dist/                   # Built React app (served by FastAPI)
  ui/                         # React source (Vite project)
  output/
    submission.csv
    bias_report.json
    interview_pack.json
```

---

## Setup

### Local (Python + Node)

```bash
# 1. Clone and enter the project
cd prismrank

# 2. Create a virtual environment
python -m venv venv
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # macOS / Linux

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set your Gemini API key
# Windows PowerShell:
$env:GEMINI_API_KEY = "your_key_here"
# macOS / Linux:
export GEMINI_API_KEY="your_key_here"

# 5. Place the candidate data
# Copy candidates.jsonl into data/candidates.jsonl

# 6. Build the frontend
cd ui
npm install
npm run build
cd ..

# 7. Start the backend
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080

# 8. Open the dashboard
# http://localhost:8080
```

### Development (Vite dev server + backend)

```bash
# Terminal 1: start the backend
cd prismrank
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080

# Terminal 2: start the Vite dev server
cd prismrank/ui
npm run dev

# Open http://localhost:5173
```

### Without Gemini API Key

The pipeline runs fully without a Gemini key. Degraded behavior:

- JD parsing uses a rule-based regex fallback
- LLM scores default to 0.5 for all candidates (ranking is driven by behavioral + trajectory signals)
- Persona cluster names default to "Cluster 1", "Cluster 2", etc.
- Recruiter chat uses keyword-based query parsing instead of Gemini

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| GEMINI_API_KEY | No | Google AI Studio key for LLM re-ranking, JD parsing, and chat |

Get a key at: https://aistudio.google.com/app/apikey

---

## Outputs

| File | Description |
|---|---|
| `output/submission.csv` | Top-100 ranked candidates with scores and reasoning |
| `output/bias_report.json` | Full fairness audit across 5 dimensions |
| `output/interview_pack.json` | 5 tailored interview questions per top-20 candidate |

---

## Competition Entry

Submitted to the **India Runs Data & AI Challenge** by Redrob.
Challenge: Intelligent Candidate Discovery and Ranking over a 100,000-profile synthetic dataset.
