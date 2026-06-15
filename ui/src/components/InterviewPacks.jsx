import { useEffect, useState } from 'react'

const TYPE_DOT = {
  behavioral: 'var(--accent)',
  technical:  'var(--gold)',
  culture:    'var(--ok-green)',
}

function QuestionCard({ q }) {
  const type = (q.type || '').toLowerCase()
  const dotColor = TYPE_DOT[type] || 'var(--ink-faint)'
  return (
    <div style={{ display: 'flex', gap: 14 }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%',
        background: dotColor, flexShrink: 0, marginTop: 7,
      }} />
      <div>
        <span style={{
          fontFamily: 'Inter', fontWeight: 600, fontSize: 10,
          textTransform: 'uppercase', letterSpacing: '0.08em',
          color: dotColor,
          display: 'block', marginBottom: 5,
        }}>
          {q.type || 'general'}
        </span>
        <p style={{
          fontFamily: 'Fraunces', fontWeight: 600, fontStyle: 'italic',
          fontSize: 16, color: 'var(--ink)', lineHeight: 1.5, marginBottom: 6,
        }}>
          {q.question}
        </p>
        {q.what_to_listen_for && (
          <p style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--ink-faint)', lineHeight: 1.6 }}>
            <span style={{ fontWeight: 500 }}>Listen for: </span>
            {q.what_to_listen_for}
          </p>
        )}
      </div>
    </div>
  )
}

function Pack({ pack, index }) {
  const [open, setOpen] = useState(index === 0)
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--rule)', marginBottom: 2 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 16,
          padding: '18px 24px', background: 'none', border: 'none', cursor: 'pointer',
          transition: 'background 150ms ease',
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-secondary)'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
      >
        <span style={{
          fontFamily: 'Fraunces', fontWeight: 900, fontSize: 22,
          color: 'var(--gold)', width: 36, flexShrink: 0, lineHeight: 1,
          textAlign: 'right',
        }}>
          {String(index + 1).padStart(2, '0')}
        </span>
        <div style={{ flex: 1, textAlign: 'left' }}>
          <p style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 17, color: 'var(--ink)' }}>
            {pack.candidate_name}
          </p>
          <p style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: 'var(--ink-faint)', marginTop: 2, letterSpacing: '-0.02em' }}>
            {pack.candidate_id}
          </p>
        </div>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: 'var(--ink-faint)', marginRight: 10 }}>
          {pack.questions?.length || 0} questions
        </span>
        <span style={{
          color: 'var(--ink-faint)', fontSize: 13, flexShrink: 0,
          transform: open ? 'rotate(180deg)' : 'none',
          transition: 'transform 250ms ease',
          display: 'inline-block',
        }}>
          ▼
        </span>
      </button>

      {open && (
        <div style={{
          padding: '0 24px 24px 76px',
          borderTop: '1px solid var(--rule)',
          display: 'flex', flexDirection: 'column', gap: 20,
          paddingTop: 20,
          animation: 'card-in 250ms ease-out both',
        }}>
          {(pack.questions || []).map((q, i) => (
            <QuestionCard key={i} q={q} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function InterviewPacks() {
  const [packs, setPacks] = useState([])
  const [loading, setLoading] = useState(true)
  const [empty, setEmpty] = useState(false)

  useEffect(() => {
    fetch('/api/download/interview-pack')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { setPacks(data); setLoading(false) })
      .catch(() => { setEmpty(true); setLoading(false) })
  }, [])

  if (loading) {
    return (
      <p style={{ fontFamily: 'Fraunces', fontStyle: 'italic', fontSize: 15, color: 'var(--ink-faint)' }}>
        Loading interview packs…
      </p>
    )
  }

  if (empty || !packs.length) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 320, gap: 14 }}>
        <svg width="44" height="44" viewBox="0 0 44 44" fill="none" opacity="0.25">
          <rect x="8" y="4" width="28" height="36" rx="1" stroke="var(--ink)" strokeWidth="1.5" fill="none"/>
          <line x1="14" y1="13" x2="30" y2="13" stroke="var(--ink)" strokeWidth="1.2"/>
          <line x1="14" y1="19" x2="30" y2="19" stroke="var(--ink)" strokeWidth="1.2"/>
          <line x1="14" y1="25" x2="24" y2="25" stroke="var(--ink)" strokeWidth="1.2"/>
        </svg>
        <p style={{ fontFamily: 'Fraunces', fontStyle: 'italic', fontSize: 16, color: 'var(--ink-faint)' }}>
          Interview packs appear for top candidates after ranking.
        </p>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 840 }}>
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontFamily: 'Fraunces', fontWeight: 900, fontSize: 36, color: 'var(--ink)', letterSpacing: '-0.02em', marginBottom: 10 }}>
          Interview Packs
        </h2>
        <div style={{ height: 1, background: 'var(--rule)' }} />
      </div>
      {packs.map((p, i) => <Pack key={p.candidate_id} pack={p} index={i} />)}
    </div>
  )
}
