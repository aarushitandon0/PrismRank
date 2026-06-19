---
title: PrismRank
emoji: 🎯
colorFrom: orange
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# PrismRank

**AI-native candidate ranking and talent intelligence system.**
Built for the [India Runs Data & AI Challenge](https://indiaruns.in) — Intelligent Candidate Discovery & Ranking by Redrob.

---

## Overview

PrismRank is a production-grade talent intelligence pipeline that ingests 100,000+ structured candidate profiles, runs a three-stage retrieval and re-ranking system, and surfaces a bias-audited shortlist of the top 100 candidates for a given job description.

The system was designed around the specific failure modes embedded in the challenge dataset: keyword-stuffed profiles, honeypot candidates with statistically impossible signals, and consulting-only careers claiming deep AI/ML expertise. Every scoring component directly targets at least one of these failure modes.

**Capabilities at a glance:**

- Three-stage retrieval: TF-IDF pre-filter (100K to 1K) + FAISS dense search (1K to 200) + Gemini LLM re-ranking (200 to 100)
- Five-component weighted score fusion with JD-specific multipliers
- Eight-signal honeypot detector with score-based suppression
- Trajectory scorer: velocity x tier progression x tenure stability
- Twelve-signal behavioral scorer over Redrob platform data
- KMeans persona clustering (k=5) with Gemini-generated archetype names
- Five-dimension fairness audit with Gini coefficient + skew ratio analysis
- Automated interview pack generation (5 tailored questions per top-20 candidate)
- Full React dashboard with recruiter chat, persona explorer, and bias report viewer
- Graceful degraded mode when no Gemini API key is present

---

## Two Execution Modes

PrismRank ships two distinct entrypoints with different purposes:

| Entrypoint | Purpose | Uses Gemini? | Network? |
|---|---|---|---|
| `scripts/rank.py` | Produces the official submission CSV. This is what gets reproduced at Stage 3. | No | No |
| `src/api/` + `ui/` (interactive dashboard) | Live demo and exploration: recruiter chat, persona naming, interview pack generation, richer JD parsing. Not used to produce the scored submission. | Optional | Optional |

`scripts/rank.py` and everything it imports (`candidate_processor`, `embedder`, `behavioral`, `trajectory`, `honeypot`, `jd_local`, `local_scorer`, `fusion`) contain zero references to `google.generativeai` or any other hosted LLM SDK. This was verified by inspecting `sys.modules` after importing the script: only the empty `google` namespace package loads (a transitive stub from the torch/protobuf dependency chain), never `google.generativeai`.

In place of Gemini's `skill_alignment`, `experience_fit`, and `culture_fit` scores, `scripts/rank.py` substitutes local, equally real signals (see `src/pipeline/local_scorer.py`):

- `skill_alignment` -- the FAISS cosine similarity score already computed during retrieval, not a placeholder
- `experience_fit` -- a piecewise function comparing the candidate's years of experience against the JD's extracted seniority floor
- `culture_fit` -- keyword overlap between the candidate's role history and the JD's extracted culture signals

Every other component of the fusion score (the JD-specific multipliers, honeypot suppression, trajectory boost, behavioral scoring) was already fully local and rule-based, so it carries over to the compliant script unchanged.

---

## Compute Constraint Compliance

The hackathon requires the ranking step to complete in 5 minutes wall-clock, on CPU only, with no network calls, under 16GB RAM and 5GB disk. Measured on the full 100,000-candidate dataset:

| Constraint | Limit | Measured | How it's satisfied |
|---|---|---|---|
| Runtime | <= 5 min | ~87s internal / ~2m41s wall-clock including Python startup | Two-phase design: an untimed pre-computation pass warms three disk caches, so the timed run only ever hits warm caches |
| Memory | <= 16 GB | Well under (single CPU process, no batching beyond 100K dicts + a 1,000 x 384 float32 matrix) | No GPU tensors, no full-dataset embedding held in memory at once |
| Compute | CPU only | CPU only | `faiss-cpu`, CPU-only PyTorch build, scikit-learn -- no CUDA dependency anywhere |
| Network | Off | Zero calls | `scripts/rank.py`'s import graph never touches `google.generativeai`; verified via `sys.modules` inspection |
| Disk | <= 5 GB | A few hundred MB (cached candidate pickle, TF-IDF vectorizer + sparse matrix, 1,000 x 384 embedding cache) | Caches are content-keyed by file size/mtime, not duplicated per run |

### Why two scripts, not one

Fitting a TF-IDF vectorizer over 100,000 documents from scratch took roughly 4 minutes by itself in testing, which alone would blow the 5-minute budget before any retrieval or scoring even started. The hackathon spec explicitly allows for this: *"pre-computation may exceed the 5-minute window, but the ranking step that produces the CSV must complete within it."*

```bash
# Step 1 -- one-time setup, NOT timed. Run this once.
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
python scripts/precompute.py --candidates data/candidates.jsonl --jd data/job_description.txt

# Step 2 -- the timed ranking step. Completes in well under 5 minutes.
python scripts/rank.py --candidates data/candidates.jsonl --jd data/job_description.txt --out submission.csv
```

`scripts/precompute.py` warms three caches under `output/precompute_cache/` and `output/embedding_cache/`:
1. The parsed candidate list (pickled, skips re-parsing 100,000 JSON lines)
2. The fitted TF-IDF vectorizer and sparse matrix over the candidate corpus (the single most expensive step; cached so the timed run only does a fast `.transform()` on the JD)
3. Sentence-transformer embeddings for the JD-relevant candidate subset (via `src/pipeline/embedder.py`'s existing content-keyed cache)

Caches are keyed by the candidates file's size and modification time, so they invalidate automatically if the dataset changes, and re-running `precompute.py` is a fast no-op once warm.

### Honeypot exclusion

`scripts/rank.py` does not rely solely on the honeypot suppression multiplier. Any candidate with `honeypot_score >= 0.55` is explicitly excluded from the top 100 before ranks are assigned, with a sorted-by-score backfill if fewer than 100 clean candidates remain in the retrieval pool. This guarantees the submission's honeypot rate stays under the 10% Stage 3 disqualification threshold rather than depending on score suppression alone.

---

## System Architecture

```
  ┌─────────────────────────────────────────────────────────────┐
  │                   candidates.jsonl                          │
  │                   100,000 profiles                          │
  └─────────────────────────┬───────────────────────────────────┘
                            │
                            ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                  CandidateProcessor                         │
  │                                                             │
  │  parse_jsonl()   ──►  _build_profile_text()                 │
  │                       (headline + summary + career titles   │
  │                        + role descriptions + skills +       │
  │                        education + certifications)          │
  │                                                             │
  │  _extract_features()                                        │
  │  ├── top_skills (endorsement + proficiency-weighted)        │
  │  ├── education_tier_score  (tier_1=4, tier_2=3 ...)         │
  │  ├── avg_tenure_months  (from career_history durations)     │
  │  └── open_to_work, redrob signals, yoe, location           │
  └─────────────────────────┬───────────────────────────────────┘
                            │
              ┌─────────────┴──────────────┐
              │                            │
              ▼                            ▼
  ┌───────────────────┐        ┌───────────────────────┐
  │  JD Parser        │        │  Stage 1: TF-IDF      │
  │                   │        │  Pre-filter            │
  │  Gemini 2.0 Flash │        │                       │
  │  extracts:        │        │  TfidfVectorizer       │
  │  - hard_skills    │        │  bigram, sublinear_tf  │
  │  - soft_skills    │        │  max_features=20,000   │
  │  - deal_breakers  │        │  min_df=2              │
  │  - seniority      │        │                       │
  │  - yoe_range      │        │  cosine_similarity     │
  │                   │        │  (JD vec vs 100K)      │
  │  Fallback: regex  │        │                       │
  │  rule-based       │        │  100,000 → 1,000       │
  └────────┬──────────┘        │  in < 1 second CPU     │
           │                   └───────────┬───────────┘
           │                               │
           │                               ▼
           │                   ┌───────────────────────┐
           │                   │  Stage 2: FAISS Dense │
           │                   │  Retrieval             │
           │                   │                       │
           │                   │  all-MiniLM-L6-v2     │
           │                   │  384-dim embeddings    │
           │                   │  IndexFlatIP           │
           │                   │  (normalized dot prod) │
           │                   │                       │
           │                   │  Cache: MD5-keyed .npy │
           │                   │  1,000 → 200 candidates│
           └───────────────────┴───────────┬───────────┘
                                           │
                                           ▼
                               ┌───────────────────────┐
                               │  Stage 3: Gemini      │
                               │  LLM Re-ranking        │
                               │                       │
                               │  Batches of 10        │
                               │  Per candidate:       │
                               │  - skill_alignment    │
                               │  - experience_fit     │
                               │  - culture_fit        │
                               │  - gap_alert (str)    │
                               │  - standout_signal    │
                               │  - one_line_summary   │
                               └───────────┬───────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
  ┌───────────────────┐        ┌───────────────────────┐   ┌───────────────────┐
  │  Behavioral       │        │  Trajectory Scorer    │   │  Honeypot         │
  │  Scorer           │        │                       │   │  Detector         │
  │                   │        │  velocity_score       │   │                   │
  │  12 Redrob        │        │  = seniority_climb /  │   │  8 independent    │
  │  platform signals │        │    (yoe * 0.5)        │   │  signals          │
  │                   │        │                       │   │                   │
  │  connection_count │        │  tier_progression     │   │  → honeypot_score │
  │  endorsements     │        │  = company_size trend │   │    (0.0 to 1.0)   │
  │  response_rate    │        │    for last 2 roles   │   │                   │
  │  interview_rate   │        │                       │   │  is_honeypot      │
  │  offer_rate       │        │  tenure_score         │   │  = score >= 0.55  │
  │  github_score     │        │  = f(avg months/role) │   │                   │
  │  saved_30d        │        │                       │   │  suppression mult │
  │  assessments      │        │  composite =          │   │  = 1 - score*0.8  │
  │  verified_contact │        │  vel*0.4 + tier*0.3   │   └────────┬──────────┘
  │  linkedin         │        │  + tenure*0.3         │            │
  │  open_to_work     │        │                       │            │
  │  completeness     │        │  → percentile + label │            │
  └────────┬──────────┘        └───────────┬───────────┘            │
           │                               │                         │
           └───────────────────────────────┼─────────────────────────┘
                                           │
                                           ▼
                               ┌───────────────────────┐
                               │    Fusion Scorer       │
                               │                       │
                               │  weighted_score =     │
                               │    skill_align * 0.30 │
                               │  + exp_fit     * 0.25 │
                               │  + behavioral  * 0.20 │
                               │  + redrob_sig  * 0.15 │
                               │  + culture_fit * 0.10 │
                               │                       │
                               │  + JD multipliers     │
                               │  + trajectory boost   │
                               │  + assessment boost   │
                               │  × honeypot suppress  │
                               │                       │
                               │  → tier A/B/C         │
                               │  → reasoning string   │
                               └───────────┬───────────┘
                                           │
              ┌────────────────────────────┼─────────────────────────────┐
              │                            │                             │
              ▼                            ▼                             ▼
  ┌───────────────────┐        ┌───────────────────────┐   ┌────────────────────┐
  │  KMeans           │        │  Bias Audit            │   │  Interview Pack    │
  │  Clustering       │        │                       │   │  Generator         │
  │                   │        │  5 fairness dims       │   │                   │
  │  k=5 over FAISS   │        │  Gini coefficient     │   │  Top 20 candidates │
  │  embeddings of    │        │  Skew ratios          │   │  5 questions each  │
  │  top-100          │        │  Shortlist vs pool    │   │  Gemini-generated  │
  │                   │        │                       │   │  from career +     │
  │  Gemini names     │        │  → audit_passed       │   │  JD hard skills    │
  │  each cluster     │        │  → warnings           │   └────────────────────┘
  │  by archetype     │        │  → recommendation     │
  └───────────────────┘        └───────────────────────┘
                                           │
                                           ▼
                               ┌───────────────────────┐
                               │    Outputs             │
                               │                       │
                               │  submission.csv       │
                               │  bias_report.json     │
                               │  interview_pack.json  │
                               └───────────────────────┘
```

---

## Pipeline Deep Dive

### Stage 1 — TF-IDF Pre-filter

Reduces 100,000 candidates to 1,000 using sparse lexical retrieval. This stage runs entirely on CPU and completes in under one second.

```
TfidfVectorizer(
    max_features = 20,000      # vocabulary cap
    ngram_range  = (1, 2)      # unigrams + bigrams
    sublinear_tf = True        # log(1 + tf) dampening
    strip_accents = "unicode"  # normalise diacritics
    min_df       = 2           # drop hapax legomena
)

scores = cosine_similarity(jd_vec, candidate_matrix)
top_indices = argsort(scores)[::-1][:1000]
```

The profile text fed into TF-IDF is a concatenation of structured fields: headline, summary, role titles, role descriptions, skill names, degree, field of study, institution, and certifications. This ensures the lexical match covers both explicit keywords and implicit domain vocabulary.

### Stage 2 — FAISS Dense Retrieval

Encodes the pre-filtered 1,000 candidates using `all-MiniLM-L6-v2` (384-dimensional sentence embeddings). Embeddings are normalized and indexed with `IndexFlatIP` (inner product on unit vectors equals cosine similarity).

```
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(
    texts,
    batch_size        = 256,
    normalize_embeddings = True,
    convert_to_numpy  = True,
)

index = faiss.IndexFlatIP(384)
index.add(embeddings)
scores, indices = index.search(jd_vector, k=200)
```

Embeddings are cached to disk using an MD5 key derived from the model name and the first 50 profile texts, allowing subsequent runs to skip re-encoding entirely.

### Stage 3 — Gemini 2.0 Flash Re-ranking

Each of the 200 candidates is scored by Gemini 2.0 Flash in batches of 10. The LLM receives the job description and a structured candidate summary, and returns a JSON object per candidate:

```json
{
  "skill_alignment":  0.0 - 1.0,
  "experience_fit":   0.0 - 1.0,
  "culture_fit":      0.0 - 1.0,
  "gap_alert":        "free text description of skill or experience gaps",
  "standout_signal":  "free text description of exceptional signal",
  "one_line_summary": "recruiter-facing single sentence"
}
```

The LLM scores are grounded in career history, not keyword lists, which is the key differentiator from the TF-IDF and FAISS stages. A candidate listing "PyTorch" as a skill but having zero AI roles in their career receives a low `skill_alignment` from Gemini even if they passed the lexical stages.

---

## Score Fusion

The final score for each candidate is computed as a weighted linear combination of five signals, followed by additive and multiplicative modifiers.

### Base Weights

| Signal | Weight | Source |
|---|---|---|
| `skill_alignment` | 30% | Gemini 2.0 Flash |
| `experience_fit` | 25% | Gemini 2.0 Flash |
| `behavioral_score` | 20% | 12-signal Redrob scorer |
| `redrob_signals` | 15% | Platform activity (completeness, notice, views) |
| `culture_fit` | 10% | Gemini 2.0 Flash |

```
weighted = (
    skill_alignment  * 0.30
    + experience_fit * 0.25
    + behavioral     * 0.20
    + redrob_score   * 0.15
    + culture_fit    * 0.10
)
```

### Post-Weighting Modifiers

Applied in sequence before the JD multiplier:

| Condition | Effect |
|---|---|
| `gap_alert` contains a JD deal-breaker keyword | `× 0.60` |
| Trajectory percentile above 85th | `× 1.08` (capped at 1.0) |
| 2+ skill assessments matching JD hard skills, avg above 75 | `× 1.05` (capped at 1.0) |
| Not open-to-work and notice period above 90 days | `× 0.95` |

### JD-Specific Multipliers

These multipliers are specific to the Senior AI Engineer (Redrob AI) job description. They target the failure modes the challenge explicitly mentions.

| Condition | Multiplier | Rationale |
|---|---|---|
| Consulting-only career (TCS/Infosys/Wipro/etc.) | `× 0.50` | JD explicit: "people who have only worked at consulting firms" |
| Non-technical title with 3+ AI skill claims | `× 0.45` | Title-skill trap the JD warns about |
| CV/Speech specialist without NLP/IR background | `× 0.70` | Off-domain ML without retrieval grounding |
| Inactive 180+ days and response rate below 15% | `× 0.75` | Effectively unreachable candidate |
| India-based candidate | `× 1.08` | JD preferred location: Pune, Noida, major Indian cities |
| Product company background | `× 1.05` | JD preference for non-services background |
| Sub-30-day notice period | `× 1.04` | JD explicit: "we love sub-30-day notice" |
| 5+ core JD skill matches | `× 1.07` | embeddings, FAISS, ranking, NLP/IR, Python, LLM |
| YoE in 4-10 year range | `× 1.02` | JD ideal band |

All boosts are capped so the multiplied weighted score cannot exceed 1.0. Penalties compound multiplicatively.

### Honeypot Suppression

After all modifiers, if a candidate's `honeypot_score` is non-zero, a suppression multiplier is applied:

```
honeypot_multiplier = 1.0 - (honeypot_score * 0.8)
final_score = weighted * honeypot_multiplier
```

A candidate with `honeypot_score = 0.80` receives a `0.36×` suppression, effectively removing them from the top 100 regardless of LLM scores.

### Tier Assignment

```
tier = "A"  if final_score >= 0.78
tier = "B"  if final_score >= 0.58
tier = "C"  otherwise
```

`exceptional_fit = True` when `behavioral > 0.80 AND skill_alignment > 0.85 AND honeypot_score < 0.20`.

---

## Behavioral Scorer

Scores 12 Redrob platform signals on a 0-1 scale. Each signal is independently weighted and additive, with the total capped at 1.0.

| Signal | Max Contribution | Threshold |
|---|---|---|
| `connection_count` | 0.08 | 500+ |
| `endorsements_received` | 0.10 | 20+ |
| `recruiter_response_rate` | 0.12 | >80% |
| `interview_completion_rate` | 0.12 | >80% |
| `offer_acceptance_rate` | 0.10 | >70% |
| `profile_completeness_score` | 0.10 | >90% |
| `github_activity_score` | 0.12 | >70 |
| `saved_by_recruiters_30d` | 0.08 | 10+ |
| `skill_assessment_scores` (presence) | 0.08 | any scores present |
| `skill_assessment_scores` (quality) | 0.02 | per score above 80 |
| `verified_email + verified_phone` | 0.06 | both verified |
| `linkedin_connected` | 0.04 | connected |
| `open_to_work_flag` | 0.05 | true |

---

## Trajectory Scorer

Evaluates career momentum across three independent dimensions.

### Velocity Score

Measures how fast a candidate climbed the seniority ladder relative to their years of experience.

```
seniority_levels = [map_title_to_level(role.title) for role in career]
# Levels: intern=0, junior=1, mid=2, senior=3, lead=4, staff=5,
#         principal=6, head/director=7, vp=8, cto/ceo=9

starting_level = seniority_levels[-1]   # oldest role
peak_level     = max(seniority_levels)
climb          = peak_level - starting_level

velocity_score = min(climb / (yoe * 0.5), 1.0)
```

### Tier Progression Score

Measures whether the candidate is moving toward larger companies.

```
company_size_map: 1-10=1, 11-50=2, 51-200=3, ..., 10001+=8

sizes = [size_of(role) for role in career[:2]]  # last 2 roles

if sizes[0] >= sizes[1]:       # moved to same-size or larger
    tier_progression = 0.80 + min((sizes[0] - sizes[1]) * 0.05, 0.20)
else:                           # moved to smaller company
    tier_progression = max(0.30, 0.50 - (sizes[1] - sizes[0]) * 0.05)
```

### Tenure Score

Penalizes chronic job-hopping and long stagnation equally.

```
avg_tenure_months -> score
< 12 months       -> 0.20  (chronic hopper)
12-24 months      -> 0.20 + (avg-12)/12 * 0.40  (improving)
24-48 months      -> 1.00  (optimal)
48-72 months      -> 1.00 - (avg-48)/24 * 0.40  (slightly long)
> 72 months       -> 0.60  (stagnant)
```

### Composite + Labels

```
composite = velocity*0.40 + tier_progression*0.30 + tenure*0.30
percentile = composite * 100

label = "Rocket"         if velocity > 0.70 and percentile > 70
      | "Steady Climber" if percentile > 60
      | "Veteran"        if velocity < 0.30 and tenure > 0.70
      | "Early Stage"    if yoe < 3
      | "Lateral Mover"  otherwise
```

---

## Honeypot Detection

The challenge dataset contains approximately 80 trap candidates with subtly impossible profiles. Any submission with more than 10% honeypots in the top 100 is disqualified. PrismRank detects these via eight independent signals, each contributing a penalty to a composite `honeypot_score`.

```
honeypot_score = min(sum(signal_penalties), 1.0)
is_honeypot    = honeypot_score >= 0.55
```

| Signal | Penalty | Condition |
|---|---|---|
| **Temporal impossibility** | +0.45 | `claimed_yoe > (current_year - graduation_year) + 3` |
| **Title-skill mismatch** | +0.35 | Non-technical title with 3+ advanced AI/ML skills |
| **Signal saturation** | +0.30 | 5+ of 6 behavioral metrics simultaneously maxed (completeness >=98, GitHub >=95, interview rate >=0.99, response rate >=0.99, verified contact, saved 30d >=50) |
| **Assessment score suspicion** | +0.40 | All assessments scored exactly 100.0, or spread <2 points across 4+ skills |
| **Keyword stuffing** | +0.40 | 5+ AI/ML skills claimed with zero supporting career evidence in role titles or descriptions |
| **Consulting-only career** | +0.25 | All companies are consulting firms (JD explicit disqualifier) |
| **Ghost candidate** | +0.20 | Claims open-to-work but inactive 180+ days, response rate below 10% |
| **Experience inflation** | +0.15 | 9+ career roles with average tenure below 10 months |

Detection example: A "Marketing Manager" with 8 years experience, listing PyTorch/BERT/RAG/LangChain/FAISS as advanced skills, with all assessment scores at exactly 97.0, graduated 2018, would accumulate +0.35 (title-skill) + +0.40 (uniform assessments) + +0.40 (keyword stuffing) = 1.15 → capped at 1.0 → `is_honeypot = True`.

---

## Bias Audit

Five fairness dimensions are computed by comparing the shortlist (top 20% by score) against the full ranked candidate pool. Audit results are written to `output/bias_report.json`.

### Dimension 1: Education Tier Concentration

```
skew_ratio = shortlist_share_tier_N / pool_share_tier_N
warning    = skew_ratio > 1.5
```

### Dimension 2: Geography Concentration (Gini Coefficient)

```
country_shares = [count / total for count in country_value_counts]

gini = (2 * sum(i * x_i for i, x_i in enumerate(sorted(shares), 1))
        / (n * sum(shares))) - (n+1)/n

warning = gini > 0.6     # 0 = perfectly even, 1 = one country dominates
```

### Dimension 3: Experience Distribution

```
skew_under3 = pool_share_under3yr / shortlist_share_under3yr
skew_over15 = pool_share_over15yr / shortlist_share_over15yr
warning      = skew_under3 > 1.5 or skew_over15 > 1.5
```

### Dimension 4: Completeness Bias

```
score_skew = top20pct_avg_score / pool_avg_score
warning    = score_skew > 2.0
```

### Dimension 5: Relocation Bias

```
skew_reloc = shortlist_willing_to_relocate / pool_willing_to_relocate
warning    = skew_reloc > 1.5
```

### Results from the Competition Run

| Dimension | Result | Warning |
|---|---|---|
| Education tier 1 concentration | 2.44x skew | YES — top-tier education over-represented |
| Geography Gini | 0.675 | YES — India dominates the shortlist |
| Under-3yr exclusion | 4.6x skew | YES — early-career candidates systematically excluded |
| Completeness bias | 1.82x | No |
| Relocation bias | 1.21x | No |

`audit_passed = false` with three active warnings. These results are expected: the JD targets a senior role requiring 5+ years experience (explaining under-3yr exclusion), prefers India-based candidates (explaining geography concentration), and selects for candidates with strong quantitative backgrounds (correlating with tier-1 education).

---

## Persona Clustering

After the final shortlist is produced, the 384-dimensional FAISS embeddings for the top 100 candidates are clustered into 5 groups using KMeans (`sklearn.cluster.KMeans(n_clusters=5)`). Gemini 2.0 Flash then names each cluster based on the titles, skills, and career patterns of its members.

Example archetype names generated during competition run:

- "Product-Focused NLP Engineers" (candidates from consumer tech with retrieval + NLP background)
- "Research-to-Industry Transitioners" (ex-PhD/research scientists moving to applied ML)
- "Platform AI Builders" (candidates with heavy infra + MLOps background)
- "Early-Career High-Velocity" (3-6yr exp with steep trajectory scores)
- "Senior ML Generalists" (10+ yr with broad ML background, less specialization)

---

## Stack

| Layer | Technology | Version |
|---|---|---|
| Runtime | Python | 3.11 |
| API framework | FastAPI + Uvicorn | latest |
| LLM | Gemini 2.0 Flash | `gemini-2.0-flash` |
| Embeddings | sentence-transformers, all-MiniLM-L6-v2 | latest |
| Vector index | FAISS, IndexFlatIP | latest |
| Lexical retrieval | scikit-learn TfidfVectorizer | latest |
| Clustering | scikit-learn KMeans | latest |
| Cosine similarity | scikit-learn cosine_similarity | latest |
| Data processing | pandas, numpy | latest |
| Frontend | React 18 | 18.x |
| Build tool | Vite | 5.x |
| Styling | Tailwind CSS + custom CSS variables | latest |
| Display font | Fraunces (variable) | Google Fonts |
| Body font | Inter | Google Fonts |
| Mono font | JetBrains Mono | Google Fonts |

---

## Project Structure

```
prismrank/
  data/
    candidates.jsonl            # 100K candidate profiles (not committed)
    job_description.txt         # Target JD for the challenge

  src/
    config.py                   # Score weights, seniority map, company size map,
                                # education tier map, model names, paths

    api/
      main.py                   # FastAPI app entrypoint, static file serving
      routes.py                 # /api/rank, /api/chat, /api/status, /api/reset-lock
      schemas.py                # Pydantic request/response models

    pipeline/
      candidate_processor.py    # JSONL parsing, profile text builder, feature extractor
      embedder.py               # TF-IDF pre-filter, sentence-transformer encoding,
                                # FAISS index builder, embedding cache management
      precompute_cache.py       # Disk caches for the compliant ranker (candidates, TF-IDF)
      jd_local.py                # LOCAL JD parser, zero LLM SDK imports (used by rank.py)
      jd_parser.py              # JD parsing via Gemini; regex fallback (dashboard only)
      local_scorer.py            # LOCAL substitutes for skill_alignment/experience_fit/
                                # culture_fit + fact-grounded reasoning generator
      llm_scorer.py             # Gemini re-ranking, batched 10 candidates/call (dashboard only)
      behavioral.py             # 12-signal Redrob behavioral scorer
      trajectory.py             # Velocity x tier progression x tenure scorer
      honeypot.py               # 8-signal trap candidate detector
      fusion.py                 # Weighted fusion, JD multipliers, honeypot suppression
      clustering.py             # KMeans clustering, Gemini archetype naming (dashboard only)
      bias_audit.py             # Gini coefficient, skew ratio fairness audit
      interview_gen.py          # Interview pack generation (dashboard only)

    frontend/
      dist/                     # Compiled React app (served by FastAPI at /)

  ui/                           # React source (Vite project)
    src/
      components/               # Dashboard, RankTable, PersonaCard, BiasReport,
                                # RecruiterChat, InterviewPack
    index.html                  # Font imports (Fraunces, Inter, JetBrains Mono)
    vite.config.js              # Dev proxy to :8080, outDir to ../src/frontend/dist

  scripts/
    rank.py                     # COMPLIANT ranking entrypoint -- produces the submission CSV.
                                # Zero network calls, zero LLM SDK imports, CPU only.
    precompute.py                # Untimed cache-warming pass, run once before rank.py
    run_pipeline.py             # Gemini-enabled standalone CLI demo runner (not for submission)

  output/
    submission.csv              # Top-100 ranked candidates with scores
    bias_report.json            # Full fairness audit
    interview_pack.json         # 5 questions x top-20 candidates
    embedding_cache/            # Cached .npy embedding arrays
    precompute_cache/            # Cached parsed candidates + TF-IDF vectorizer/matrix

  requirements.txt
  submission_metadata.yaml
  .gitignore
  README.md
```

---

## Setup

### Reproducing the submission CSV (the only path that matters for Stage 3)

```bash
pip install -r requirements.txt

# Place candidates.jsonl and job_description.txt in data/

# One-time, untimed setup
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
python scripts/precompute.py --candidates data/candidates.jsonl --jd data/job_description.txt

# The timed ranking step -- completes in well under 5 minutes
python scripts/rank.py --candidates data/candidates.jsonl --jd data/job_description.txt --out submission.csv
```

No Node.js, no Gemini API key, and no network access are required for this path. The sections below cover the optional interactive dashboard.

### Prerequisites (dashboard only)

- Python 3.11+
- Node.js 18+ (for frontend build)
- Gemini API key (optional — system runs in degraded mode without one)

### Local Installation

```bash
# 1. Enter the project directory
cd prismrank

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set the Gemini API key (optional)
# Windows PowerShell:
$env:GEMINI_API_KEY = "your_key_here"

# macOS / Linux:
export GEMINI_API_KEY="your_key_here"

# 5. Place the challenge data
# Copy candidates.jsonl into data/candidates.jsonl

# 6. Build the React frontend
cd ui
npm install
npm run build
cd ..

# 7. Start the server
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080

# 8. Open the dashboard
# http://localhost:8080
```

### Development Mode (hot-reload frontend + backend)

```bash
# Terminal 1 — backend
cd prismrank
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2 — Vite dev server (proxies /api to :8080)
cd prismrank/ui
npm run dev

# Open http://localhost:5173
```

---

## Degraded Mode (no Gemini API key)

PrismRank runs the full pipeline without a Gemini API key. The following components fall back gracefully:

| Component | With Gemini | Without Gemini |
|---|---|---|
| JD Parser | Structured extraction (skills, deal-breakers, YoE range) | Regex rule-based extraction from JD text |
| LLM Re-ranker | Grounded skill and experience scores | Defaults to 0.50 for all candidates |
| Cluster naming | Gemini-generated archetype names | "Cluster 1", "Cluster 2", ... "Cluster 5" |
| Interview pack | Tailored questions grounded in career history | Template-based questions from JD hard skills |
| Recruiter chat | Conversational Gemini over ranked results | Keyword-based query matching |

All retrieval (TF-IDF, FAISS), scoring (behavioral, trajectory, honeypot), fusion, clustering, and bias audit components run identically regardless of API key availability. In degraded mode, final scores are driven by behavioral + trajectory signals.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | No | Google AI Studio API key for LLM re-ranking, JD parsing, persona naming, and recruiter chat |

Get a key at: https://aistudio.google.com/app/apikey

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/rank` | Run the full ranking pipeline. Body: `{ "candidates_path": "...", "job_description": "..." }` |
| `GET` | `/api/status` | Health check and model load status |
| `POST` | `/api/chat` | Recruiter chat query over ranked results |
| `GET` | `/api/download/submission` | Download `submission.csv` |
| `GET` | `/api/download/bias-report` | Download `bias_report.json` |
| `GET` | `/api/download/interview-pack` | Download `interview_pack.json` |
| `POST` | `/api/reset-lock` | Emergency release of the ranking lock if a job appears stuck |

---

## Outputs

### `output/submission.csv`

One row per top-100 candidate. Columns include:

```
rank, candidate_id, name, final_score, tier, exceptional_fit,
reasoning, skill_alignment, experience_fit, behavioral_score,
redrob_signals, culture_fit, trajectory_label, trajectory_percentile,
one_line_summary, gap_alert, standout_signal, top_skills,
years_experience, current_title, current_company, location, country,
education_tier_score, open_to_work, notice_period_days,
preferred_work_mode, willing_to_relocate, skill_assessment_scores,
honeypot_score
```

### `output/bias_report.json`

```json
{
  "audit_passed": false,
  "warnings": ["Education tier 1: shortlist 82% vs pool 34% (skew 2.4x)", ...],
  "metrics": {
    "edu_tier_1_concentration": { "shortlist_share": 0.82, "pool_share": 0.34, "skew_ratio": 2.44, "warning": true },
    "geography_gini": { "shortlist_gini": 0.675, "warning": true },
    "experience_distribution": { "exclusion_skew_under3": 4.6, "warning": true },
    ...
  },
  "recommendation": "..."
}
```

### `output/interview_pack.json`

```json
[
  {
    "candidate_id": "...",
    "name": "...",
    "questions": [
      "Walk me through how you designed the retrieval pipeline at [Company]. ...",
      ...
    ]
  },
  ...
]
```

---

## Competition Entry

Submitted to the **India Runs Data & AI Challenge** by Redrob.
Category: Intelligent Candidate Discovery and Ranking.
Dataset: 100,000 synthetic candidate profiles with embedded honeypots.
Target role: Senior AI Engineer — Redrob AI Platform (embeddings, vector search, ranking, LLM evaluation).
