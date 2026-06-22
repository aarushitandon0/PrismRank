---
title: PrismRank
emoji: 🎯
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# PrismRank

**AI-native candidate ranking and talent intelligence system.**

---

## Overview

PrismRank is a production-grade talent intelligence pipeline that ingests 100,000+ structured candidate profiles, runs a three-stage retrieval and re-ranking system, and surfaces a bias-audited shortlist of the top candidates for a given job description.

The system was designed around the specific failure modes embedded in the challenge dataset: keyword-stuffed profiles, honeypot candidates with statistically impossible signals, and consulting-only careers claiming deep AI/ML expertise. Every scoring component directly targets at least one of these failure modes.

**Capabilities at a glance:**

- Two-stage retrieval: TF-IDF pre-filter (100K to 1K) + FAISS dense search (1K to 200), followed by fully local, rule-based scoring (200 to 100)
- Blended skill alignment (FAISS cosine similarity + explicit hard-skill match ratio) and relevant-experience-weighted fit (career history scanned for JD-relevant roles, not just total tenure)
- Five-component weighted score fusion with JD-specific multipliers
- Eight-signal honeypot detector with hard exclusion from the top 100, not just score suppression
- Trajectory scorer: velocity x tier progression x tenure stability
- Twelve-signal behavioral scorer over Redrob platform data
- Population-relative reasoning generator: sentence structure varies by which signal is genuinely most distinctive for each candidate, not one template with values filled in
- Five-dimension fairness audit with Gini coefficient + skew ratio analysis
- An optional interactive dashboard (React + FastAPI) sharing the exact same local scoring engine, for exploration and demos, separate from the script that produces the scored submission

---

## Compute Constraint Compliance

The official submission CSV is produced by `scripts/rank.py`, a separate, network-free entrypoint from the interactive dashboard described above. It satisfies every hackathon compute constraint:

| Constraint | Limit | Measured | How it's satisfied |
|---|---|---|---|
| Runtime | <= 5 min | ~33s wall-clock on the full 100K dataset | Two-phase design: `scripts/precompute.py` (untimed) warms disk caches once; `scripts/rank.py` (timed) only ever hits warm caches |
| Memory | <= 16 GB | Well under | No GPU tensors; full raw JSON is never retained for all 100K candidates, only the lightweight extracted feature set |
| Compute | CPU only | CPU only | `faiss-cpu`, CPU-only PyTorch, scikit-learn -- zero CUDA dependency |
| Network | Off | Zero calls | `scripts/rank.py`'s entire import graph (`candidate_processor`, `embedder`, `behavioral`, `trajectory`, `honeypot`, `jd_local`, `local_scorer`, `fusion`) has zero hosted-API dependencies -- verified by inspecting `sys.modules` after import |
| Disk | <= 5 GB | A few hundred MB | Cached candidate pickle + TF-IDF vectorizer/matrix + embedding cache, content-keyed by file size/mtime |

**Reproduction (two commands, matching spec section 10.3):**

```bash
# Untimed, one-time setup
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
python scripts/precompute.py --candidates data/candidates.jsonl --jd data/job_description.txt

# Timed ranking step
python scripts/rank.py --candidates data/candidates.jsonl --jd data/job_description.txt --out submission.csv
```

**Honeypot safety margin:** any candidate scoring `honeypot_score >= 0.55` is explicitly excluded from the top 100 before ranks are assigned (not just down-weighted), with a sorted backfill if fewer than 100 clean candidates remain in the retrieval pool. This keeps the submission's honeypot rate under the 10% Stage 3 disqualification threshold with real margin.

A separate `/api/sandbox-rank` endpoint, used for the hosted sandbox/demo link, calls `scripts/rank.py`'s `run()` function directly rather than reimplementing any logic -- so the sandbox and the official submission script cannot drift out of sync.

---

## Local Scoring Engine (the compliant path, `src/pipeline/local_scorer.py`)

This is what actually produces `skill_alignment`, `experience_fit`, and `culture_fit` for the official submission. No call in this module touches a network or any hosted service. Each signal is a deterministic formula over fields already present in the candidate's profile.

### Skill Alignment

A blend of two independent signals, not a single reused value:

```
semantic = clamp(faiss_cosine_similarity, 0, 1)   # already computed during retrieval
match_ratio = (count of candidate skills overlapping JD hard_skills) / (total JD hard_skills)

skill_alignment = 0.65 * semantic + 0.35 * match_ratio
```

The blend matters because the semantic half is the same score that already determined whether a candidate survived FAISS retrieval, so using it alone would add no new information to the fusion score. The explicit match-ratio half rewards candidates who literally list the JD's named skills, independent of embedding similarity.

### Experience Fit

A blend of total tenure and *relevant* tenure, directly reflecting the job description's own distinction between total years and years specifically in applied roles:

```
relevant_years = sum(duration_months for each career role whose title or
                      description mentions a JD hard skill) / 12

band_score(value, floor) =
    1.0                          if floor <= value <= floor + 6
    max(0.25, 1 - (floor - value) * 0.15)   if value < floor
    max(0.40, 1 - (value - floor - 6) * 0.04) otherwise

total_fit     = band_score(years_experience, jd_seniority_floor)
relevant_fit  = band_score(relevant_years, jd_seniority_floor - 1.5)

experience_fit = 0.4 * total_fit + 0.6 * relevant_fit
```

Relevant years are weighted more heavily than total years. A candidate with eight years of experience where only one year touched a JD-relevant skill scores meaningfully lower than a candidate with the same total tenure spent entirely in relevant roles -- this is what catches candidates whose listed skills are not substantiated by their actual career history, exactly the trap the job description warns about. Verified during testing: a real candidate listing NLP, LoRA, and Milvus as skills, with career history entirely in Kafka/Spark data engineering roles, scored `relevant_years = 0` despite four nominal skill matches.

### Culture Fit

Keyword overlap between the candidate's career history text and the JD's extracted culture signals (a small fixed list such as "async-first," "move fast"). Intentionally narrow: the heavier JD-specific business rules (consulting penalty, product-company boost) already live in the fusion layer's multipliers, applied separately.

### Reasoning Generation

No reasoning sentence is produced by a generative model. Every sentence is assembled from a fixed set of templates filled with real fields from the candidate's profile (name, title, company, years of experience, matched skills, notice period, trajectory label).

To avoid producing the same sentence shape for every candidate, the opener's structure is chosen by which of four signals (skill, experience, trajectory, behavioral) is most distinctive for that specific candidate **relative to the rest of the final shortlist**, not by raw signal magnitude:

```
for each of the four signals, rank this candidate's value against
every other candidate in the final top-100 (percentile rank)

dominant_signal = whichever signal has this candidate's highest percentile
```

This is crossed with a confidence tier derived from rank (high for ranks 1-10, medium for 11-40, low for 41-100), giving twelve distinct structural combinations. Percentile-based comparison was a deliberate fix: an earlier version compared raw signal magnitudes directly, and because `experience_fit`'s band formula is structurally easier to score high on than the other three signals, it mechanically dominated nearly every candidate's reasoning regardless of what was actually distinctive about them. Verified by inspecting a real 100-candidate run: after the fix, dominant-signal selection was roughly evenly distributed (27 skill, 23 experience, 24 trajectory, 26 behavioral) rather than concentrated on one signal.

---

## System Architecture (Optional Interactive Dashboard)

The diagram below describes `src/api/` and the React dashboard, an optional, separate tool for exploration and demos. **It is not used to produce the official submission CSV** -- that's `scripts/rank.py`, documented above. The dashboard shares the same local scoring engine for consistency.

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
  │  (local)          │        │  Pre-filter            │
  │                   │        │                       │
  │  extracts:        │        │  TfidfVectorizer       │
  │  - hard_skills    │        │  bigram, sublinear_tf  │
  │  - soft_skills    │        │  max_features=20,000   │
  │  - deal_breakers  │        │  min_df=2              │
  │  - seniority      │        │                       │
  │  - yoe_range      │        │  cosine_similarity     │
  │                   │        │  (JD vec vs 100K)      │
  │  Hardcoded parse  │        │                       │
  │  + regex fallback │        │  100,000 → 1,000       │
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
                               │  Stage 3: Local       │
                               │  Scoring               │
                               │                       │
                               │  Per candidate:       │
                               │  - skill_alignment    │
                               │    (cosine + skill    │
                               │     match ratio)       │
                               │  - experience_fit     │
                               │    (total + relevant   │
                               │     years, blended)    │
                               │  - culture_fit         │
                               │    (keyword overlap)   │
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
  │                   │        │  5 fairness dims       │   │  (template-based)  │
  │  k=5 over FAISS   │        │  Gini coefficient     │   │  Top 20 candidates │
  │  embeddings of    │        │  Skew ratios          │   │  5 questions each  │
  │  top-100          │        │  Shortlist vs pool    │   │  from top skills + │
  │                   │        │                       │   │  gap alert         │
  │  Deterministic    │        │  → audit_passed       │   │                    │
  │  "Cluster N"      │        │  → warnings           │   └────────────────────┘
  │  numbering        │        │  → recommendation     │
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

### Stage 3 — Local Scoring

Each of the 200 candidates is scored by `src/pipeline/local_scorer.py`, computing `skill_alignment`, `experience_fit`, and `culture_fit` with the formulas documented above in "Local Scoring Engine." Zero network calls. This same module is used by both `scripts/rank.py` (the official submission script) and the interactive dashboard, so there is exactly one scoring implementation, not two that could drift apart.

---

## Score Fusion

The final score for each candidate is computed as a weighted linear combination of five signals, followed by additive and multiplicative modifiers.

### Base Weights

| Signal | Weight | Source |
|---|---|---|
| `skill_alignment` | 30% | FAISS cosine similarity blended with hard-skill match ratio |
| `experience_fit` | 25% | Total-years and relevant-years band scores, blended |
| `behavioral_score` | 20% | 12-signal Redrob scorer |
| `redrob_signals` | 15% | Platform activity (completeness, notice, views) |
| `culture_fit` | 10% | JD culture-signal keyword overlap |

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

A candidate with `honeypot_score = 0.80` receives a `0.36×` suppression, effectively removing them from the top 100 regardless of their other scores. In `scripts/rank.py`, this is further backed by a hard exclusion: any candidate at or above `honeypot_score = 0.55` is removed from consideration before ranks are even assigned, not merely down-weighted.

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

After the final shortlist is produced, the 384-dimensional FAISS embeddings for the top 100 candidates are clustered into 5 groups using KMeans (`sklearn.cluster.KMeans(n_clusters=5)`). Each cluster is given a deterministic, numbered label ("Cluster 1" through "Cluster 5") rather than a generated name, since cluster naming is a presentation detail, not part of the ranking logic.

---

## Stack

| Layer | Technology | Version |
|---|---|---|
| Runtime | Python | 3.11 |
| API framework | FastAPI + Uvicorn | latest |
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
      precompute_cache.py       # Disk caches for the ranker (parsed candidates,
                                # TF-IDF vectorizer/matrix), keyed by file size/mtime
      jd_local.py               # JD parser: hardcoded parse for the released JD,
                                # regex fallback otherwise. Zero network calls.
      local_scorer.py           # skill_alignment / experience_fit / culture_fit
                                # scorers, plus the population-aware reasoning
                                # generator. Zero network calls.
      behavioral.py             # 12-signal Redrob behavioral scorer
      trajectory.py             # Velocity x tier progression x tenure scorer
      honeypot.py               # 8-signal trap candidate detector
      fusion.py                 # Weighted fusion, JD multipliers, honeypot suppression
      clustering.py             # KMeans clustering, deterministic cluster numbering
      bias_audit.py             # Gini coefficient, skew ratio fairness audit
      interview_gen.py          # Template-based interview pack generation, top-20 candidates

    frontend/
      dist/                     # Compiled React app (served by FastAPI at /)

  ui/                           # React source (Vite project)
    src/
      components/               # Dashboard, RankTable, PersonaCard, BiasReport,
                                # RecruiterChat, InterviewPack
    index.html                  # Font imports (Fraunces, Inter, JetBrains Mono)
    vite.config.js              # Dev proxy to :8080, outDir to ../src/frontend/dist

  scripts/
    rank.py                     # COMPLIANT ranking entrypoint -- produces the official
                                # submission CSV. Zero network calls anywhere in its
                                # import graph, CPU only.
    precompute.py                # Untimed cache-warming pass, run once before rank.py

  output/
    submission.csv              # Dashboard's output (different file, different
                                # purpose -- not the submission)
    bias_report.json            # Full fairness audit
    interview_pack.json         # 5 questions x top-20 candidates
    embedding_cache/            # Cached .npy embedding arrays
    precompute_cache/            # Cached parsed candidates + TF-IDF vectorizer/matrix

  team_xxx.csv                  # The actual submission, produced by scripts/rank.py
  submission_metadata.yaml
  requirements.txt
  .gitignore
  README.md
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend build)

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

# 4. Place the challenge data
# Copy candidates.jsonl into data/candidates.jsonl

# 5. Build the React frontend
cd ui
npm install
npm run build
cd ..

# 6. Start the server
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080

# 7. Open the dashboard
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
| `POST` | `/api/sandbox-rank` | Sandbox/demo endpoint (see below) |

---

## Sandbox / Reproducibility Endpoint

`POST /api/sandbox-rank` accepts an uploaded `.jsonl` file (intended for small samples, up to 100 candidates) and calls `scripts/rank.py`'s `run()` function directly -- the exact same network-free, CPU-only code that produces the official submission CSV, not a separate reimplementation. It returns the resulting ranked CSV.

This exists specifically to satisfy a hosted sandbox requirement: a small, fast, publicly reachable way to verify the ranking code runs end-to-end before a full reproduction against the complete candidate pool. Because it calls into `scripts/rank.py` directly rather than duplicating logic, there is no way for this endpoint and the official submission script to drift out of sync.

```bash
curl -X POST https://<deployed-url>/api/sandbox-rank \
  -F "file=@small_sample.jsonl" \
  -o sandbox_submission.csv
```

Verified locally on a 50-candidate sample: completes in ~16 seconds, produces a correctly ranked CSV with fewer than 100 rows (expected -- the sandbox does not require a full 100-row output, per spec section 10.5).

---

## Outputs

### `team_xxx.csv` (the actual hackathon submission, produced by `scripts/rank.py`)

Exactly 100 rows, 4 columns, matching the hackathon's required schema:

```
candidate_id, rank, score, reasoning
```

### `output/submission.csv` (dashboard output, not the submission)

Produced by the optional interactive dashboard when run interactively. A much richer schema for the demo UI, since the dashboard surfaces every score component visually:

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
