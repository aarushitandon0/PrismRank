import { useState, useRef, useEffect } from 'react'
import DashboardCard from './DashboardCard'

const LOADING_MSGS = [
  'Parsing resumes…', 'Building semantic index…', 'Running FAISS vector search…',
  'LLM scoring top candidates…', 'Fusing behavioral signals…', 'Clustering talent personas…',
  'Running bias audit…', 'Generating interview packs…', 'Finalizing rankings…',
]

const EXAMPLE_JD = `Senior AI Engineer — Founding Team
Company: Redrob AI (Series A)
Location: Pune/Noida, India (Hybrid) | Open to relocation

We need someone simultaneously comfortable with:
1. Deep technical depth in modern ML systems — embeddings, retrieval, ranking, LLMs.
2. Scrappy product-engineering attitude — willing to ship a working ranker in a week.

Things you absolutely need:
• Production experience with embeddings-based retrieval systems
• Production experience with vector databases (FAISS, Pinecone, Weaviate, Qdrant)
• Strong Python — we care about code quality
• Hands-on experience designing evaluation frameworks (NDCG, MRR, MAP)

6-8 years total experience, of which 4-5 are in applied ML/AI roles at product companies.`

const PIPELINE_STEPS = [
  { n: '1', label: 'TF-IDF Pre-filter',  sub: 'Narrows 100K→1K' },
  { n: '2', label: 'FAISS Vector Search', sub: 'Semantic retrieval' },
  { n: '3', label: 'Gemini Re-ranking',   sub: 'LLM scores top fits' },
  { n: '4', label: 'Bias Audit',          sub: 'Fairness check' },
]

function inputStyle(mono = false) {
  return {
    width: '100%',
    background: 'var(--bg-card)',
    border: '1px solid var(--rule)',
    color: 'var(--ink)',
    fontFamily: mono ? 'JetBrains Mono' : 'Inter',
    fontSize: 13,
    transition: 'border-color 150ms ease',
  }
}

function PipelineBar({ total, shortlisted, topScore, time, biasWarning }) {
  const [display, setDisplay] = useState(0)
  useEffect(() => {
    if (!topScore) return
    let start = null
    const dur = 800
    function step(ts) {
      if (!start) start = ts
      const p = Math.min((ts - start) / dur, 1)
      const ease = 1 - Math.pow(1 - p, 2)
      setDisplay((topScore * ease).toFixed(1))
      if (p < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [topScore])

  return (
    <div style={{
      display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4,
      padding: '12px 0', borderBottom: '1px solid var(--rule)', marginBottom: 24,
    }}>
      <span style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)' }}>
        <strong style={{ fontFamily: 'Fraunces', fontWeight: 700, color: 'var(--ink)' }}>
          {(total || 0).toLocaleString()}
        </strong> scanned
      </span>
      <span style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--rule)', margin: '0 8px' }}>→</span>
      <span style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)' }}>
        <strong style={{ fontFamily: 'Fraunces', fontWeight: 700, color: 'var(--ink)' }}>
          {shortlisted}
        </strong> shortlisted
      </span>
      <span style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--rule)', margin: '0 8px' }}>→</span>
      <span style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 17, color: 'var(--gold)' }}>
        {display}
      </span>
      <span style={{ fontFamily: 'Inter', fontSize: 11, color: 'var(--ink-faint)', marginLeft: 2 }}>top score</span>
      <span style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--rule)', margin: '0 8px' }}>·</span>
      <span style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-faint)' }}>{time}s</span>
      <span style={{ flex: 1 }} />
      {biasWarning !== undefined && (
        <span style={{
          fontFamily: 'Inter', fontSize: 12, fontWeight: 500,
          color: biasWarning ? 'var(--warn-orange)' : 'var(--ok-green)',
        }}>
          {biasWarning ? '⚠ Bias warnings detected' : '✓ Bias audit passed'}
        </span>
      )}
    </div>
  )
}

function JDPreview({ jd, onRerun }) {
  const [open, setOpen] = useState(false)
  const preview = jd.split('\n').filter(Boolean).slice(0, 2).join(' ').slice(0, 120)
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--rule)',
      marginBottom: 28,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--ink-faint)' }}>
            Active Job Description
          </span>
          {!open && (
            <p style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)', marginTop: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {preview}…
            </p>
          )}
        </div>
        <div style={{ display: 'flex', gap: 10, flexShrink: 0, marginLeft: 16 }}>
          <button
            onClick={onRerun}
            style={{
              fontFamily: 'Inter', fontSize: 11, fontWeight: 600,
              textTransform: 'uppercase', letterSpacing: '0.06em',
              display: 'flex', alignItems: 'center', gap: 5, padding: '6px 14px',
              background: 'var(--accent)', color: 'var(--bg-primary)',
              border: 'none', cursor: 'pointer',
              transition: 'background 150ms ease',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--accent-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = 'var(--accent)'}
          >
            New Search
          </button>
          <button
            onClick={() => setOpen(o => !o)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-faint)', fontSize: 16, display: 'flex', alignItems: 'center' }}
          >
            {open ? '↑' : '↓'}
          </button>
        </div>
      </div>
      {open && (
        <div style={{ padding: '14px 20px', borderTop: '1px solid var(--rule)' }}>
          <pre style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)', lineHeight: 1.7, whiteSpace: 'pre-wrap', margin: 0 }}>
            {jd}
          </pre>
        </div>
      )}
    </div>
  )
}

export default function Dashboard({ rankingData, setLoading, setLoadingMsg, onRankingComplete }) {
  const [jd, setJd] = useState('')
  const [path, setPath] = useState('data/candidates.jsonl')
  const [topK, setTopK] = useState(20)
  const [error, setError] = useState('')
  const [charCount, setCharCount] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState('')
  const fileInputRef = useRef(null)
  const interval = useRef(null)

  function handleJdChange(e) {
    setJd(e.target.value)
    setCharCount(e.target.value.length)
  }

  function loadExample() {
    setJd(EXAMPLE_JD)
    setCharCount(EXAMPLE_JD.length)
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.jsonl')) {
      setError('Only .jsonl files are accepted.')
      return
    }
    setUploading(true)
    setUploadStatus('')
    setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch('/api/upload-candidates', { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      setPath(data.path)
      setUploadStatus(`Uploaded ${file.name} (${data.size_mb} MB)`)
    } catch (err) {
      setError(`Upload failed: ${err.message}`)
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  async function run() {
    if (!jd.trim()) { setError('Paste or write a job description first.'); return }
    setError('')
    setLoading(true)
    let i = 0
    setLoadingMsg(LOADING_MSGS[0])
    interval.current = setInterval(() => {
      i++
      setLoadingMsg(LOADING_MSGS[i % LOADING_MSGS.length])
    }, 3500)
    try {
      const res = await fetch('/api/rank', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jd_text: jd, candidates_path: path, top_k: topK }),
      })
      clearInterval(interval.current)
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      onRankingComplete(await res.json())
    } catch (err) {
      clearInterval(interval.current)
      setError(`Ranking failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const hasResults = rankingData?.shortlist?.length > 0
  const topScore = hasResults ? (rankingData.shortlist[0].final_score * 100).toFixed(1) : null
  const biasOk = rankingData?.bias_report?.audit_passed

  /* ── Results view ── */
  if (hasResults) {
    const sl = rankingData.shortlist
    return (
      <div>
        <PipelineBar
          total={rankingData.total_candidates}
          shortlisted={sl.length}
          topScore={parseFloat(topScore)}
          time={rankingData.processing_time_seconds}
          biasWarning={!biasOk}
        />
        <JDPreview jd={jd || '(job description not available)'} onRerun={() => onRankingComplete(null)} />

        {/* Podium layout */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <DashboardCard candidate={sl[0]} index={0} />

          {sl.length > 1 && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              {sl.slice(1, 3).map((c, i) => (
                <DashboardCard key={c.candidate_id} candidate={c} index={i + 1} />
              ))}
            </div>
          )}

          {sl.length > 3 && (
            <div style={{ border: '1px solid var(--rule)', borderBottom: 'none', marginTop: 2 }}>
              {sl.slice(3).map((c, i) => (
                <DashboardCard key={c.candidate_id} candidate={c} index={i + 3} />
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  /* ── Landing view ── */
  return (
    <div style={{ minHeight: 'calc(100vh - 160px)', display: 'flex', flexDirection: 'column' }}>

      {/* Editorial hero + form */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 56, flex: 1, alignItems: 'flex-start' }}>

        {/* Left: hero copy + pipeline */}
        <div style={{ paddingTop: 8 }}>
          <h1 style={{
            fontFamily: 'Fraunces', fontWeight: 900, fontSize: 52, lineHeight: 1.05,
            color: 'var(--ink)', letterSpacing: '-0.03em', marginBottom: 18,
          }}>
            Find your{' '}
            <em style={{ fontStyle: 'normal', color: 'var(--accent)' }}>top talent</em>
            {' '}in seconds.
          </h1>
          <p style={{
            fontFamily: 'Inter', fontWeight: 400, fontSize: 16,
            color: 'var(--ink-muted)', lineHeight: 1.7, maxWidth: 400, marginBottom: 44,
          }}>
            Paste any job description. PrismRank searches your entire candidate pool with semantic AI, re-ranks with Gemini, and surfaces the best matches with a full bias audit.
          </p>

          {/* Pipeline timeline */}
          <p style={{
            fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase',
            letterSpacing: '0.12em', color: 'var(--ink-faint)', marginBottom: 20,
          }}>
            How it works
          </p>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 0, position: 'relative' }}>
            {/* Connecting line */}
            <div style={{
              position: 'absolute', top: 17, left: 20, right: 20,
              height: 1, background: 'var(--rule)', zIndex: 0,
            }} />
            {PIPELINE_STEPS.map((s, i) => (
              <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, position: 'relative', zIndex: 1 }}>
                <div style={{
                  width: 34, height: 34, borderRadius: '50%',
                  background: 'var(--bg-card)', border: '1.5px solid var(--rule)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <span style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 13, color: 'var(--ink-muted)' }}>
                    {s.n}
                  </span>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontFamily: 'Inter', fontWeight: 500, fontSize: 12, color: 'var(--ink)', lineHeight: 1.3 }}>{s.label}</p>
                  <p style={{ fontFamily: 'Inter', fontSize: 11, color: 'var(--ink-faint)', marginTop: 2 }}>{s.sub}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: form card */}
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--rule)',
          padding: '32px',
        }}>
          {/* JD header row */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--ink-faint)' }}>
              Job Description
            </p>
            <button
              onClick={loadExample}
              style={{
                fontFamily: 'Inter', fontSize: 11, fontWeight: 500,
                color: 'var(--accent)', background: 'none', border: 'none',
                cursor: 'pointer', padding: '2px 6px',
                textDecoration: 'underline',
                transition: 'color 150ms ease',
              }}
              onMouseEnter={e => e.currentTarget.style.color = 'var(--accent-hover)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--accent)'}
            >
              Load example
            </button>
          </div>

          <div style={{ position: 'relative', marginBottom: 18 }}>
            <textarea
              value={jd}
              onChange={handleJdChange}
              placeholder="Paste the full job description — role requirements, skills, experience, culture signals…"
              rows={12}
              style={{
                ...inputStyle(true),
                resize: 'vertical',
                padding: '14px 16px',
                lineHeight: 1.65,
                fontFamily: 'JetBrains Mono',
                fontSize: 12,
              }}
              onFocus={e => e.target.style.borderColor = 'var(--gold)'}
              onBlur={e => e.target.style.borderColor = 'var(--rule)'}
            />
            <span style={{
              position: 'absolute', bottom: 10, right: 12,
              fontFamily: 'JetBrains Mono', fontSize: 9, color: 'var(--ink-faint)',
              pointerEvents: 'none',
            }}>
              {charCount} chars
            </span>
          </div>

          {/* Config row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, marginBottom: uploadStatus ? 6 : 20, alignItems: 'flex-end' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--ink-faint)', margin: 0 }}>
                  Candidates File
                </p>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  style={{
                    fontFamily: 'Inter', fontSize: 10, fontWeight: 600,
                    textTransform: 'uppercase', letterSpacing: '0.06em',
                    padding: '3px 10px',
                    background: uploading ? 'var(--bg-secondary)' : 'var(--ink)',
                    color: 'var(--bg-primary)',
                    border: 'none', cursor: uploading ? 'not-allowed' : 'pointer',
                    transition: 'background 150ms ease',
                    opacity: uploading ? 0.6 : 1,
                  }}
                >
                  {uploading ? 'Uploading…' : 'Upload .jsonl'}
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".jsonl"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </div>
              <input
                value={path}
                onChange={e => setPath(e.target.value)}
                placeholder="data/candidates.jsonl"
                style={{ ...inputStyle(true), padding: '9px 12px' }}
                onFocus={e => e.target.style.borderColor = 'var(--gold)'}
                onBlur={e => e.target.style.borderColor = 'var(--rule)'}
              />
            </div>
            <div>
              <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--ink-faint)', marginBottom: 8 }}>
                Top K
              </p>
              <input
                type="number" min={5} max={100}
                value={topK}
                onChange={e => setTopK(Number(e.target.value))}
                style={{ ...inputStyle(true), padding: '9px 12px', width: 72 }}
                onFocus={e => e.target.style.borderColor = 'var(--gold)'}
                onBlur={e => e.target.style.borderColor = 'var(--rule)'}
              />
            </div>
          </div>

          {uploadStatus && (
            <div style={{
              background: 'var(--ok-bg)',
              borderLeft: '3px solid var(--ok-green)',
              padding: '8px 14px', marginBottom: 16,
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span style={{ color: 'var(--ok-green)', fontSize: 14 }}>✓</span>
              <p style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--ok-green)', margin: 0 }}>{uploadStatus}</p>
            </div>
          )}

          {error && (
            <div style={{
              background: 'var(--warn-bg)',
              borderLeft: '3px solid var(--warn-orange)',
              padding: '10px 14px', marginBottom: 16,
            }}>
              <p style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--warn-orange)' }}>{error}</p>
            </div>
          )}

          <button
            onClick={run}
            style={{
              width: '100%', padding: '16px',
              background: 'var(--accent)', color: 'var(--bg-primary)',
              fontFamily: 'Fraunces', fontWeight: 700, fontSize: 18,
              letterSpacing: '-0.01em',
              border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
              transition: 'background 150ms ease',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--accent-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = 'var(--accent)'}
          >
            Analyze Talent Pool →
          </button>

          <p style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--ink-faint)', textAlign: 'center', marginTop: 14, lineHeight: 1.5 }}>
            First run embeds 1K candidates (~2 min). Subsequent runs load from cache (~30s).
          </p>
        </div>
      </div>
    </div>
  )
}
