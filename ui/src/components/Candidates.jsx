import { useState, useMemo } from 'react'
import CandidateProfile from './CandidateProfile'

const inputBase = {
  background: 'var(--bg-card)',
  border: '1px solid var(--rule)',
  color: 'var(--ink)',
  fontFamily: 'Inter',
  fontSize: 13,
  transition: 'border-color 150ms ease',
}

function CandidateRow({ c, onClick }) {
  const [hovered, setHovered] = useState(false)
  const score = (c.final_score || 0) * 100

  return (
    <div
      onClick={() => onClick(c)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: 18,
        padding: '18px 24px',
        background: hovered ? 'var(--bg-secondary)' : 'var(--bg-card)',
        borderBottom: '1px solid var(--rule)',
        borderLeft: hovered ? '3px solid var(--accent)' : '3px solid transparent',
        cursor: 'pointer',
        transform: hovered ? 'translateY(-1px)' : 'translateY(0)',
        boxShadow: hovered ? '0 4px 16px rgba(44,24,16,0.07)' : 'none',
        transition: 'all 200ms ease',
      }}
    >
      {/* Rank */}
      <span style={{
        fontFamily: 'Fraunces', fontWeight: 900, fontSize: 28,
        color: 'var(--rule)', width: 48, flexShrink: 0, lineHeight: 1,
      }}>
        {String(c.rank).padStart(2, '0')}
      </span>

      {/* Name + meta */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 3 }}>
          <span style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 17, color: 'var(--ink)' }}>
            {c.name}
          </span>
          <span style={{
            fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase',
            letterSpacing: '0.06em', padding: '2px 6px',
            border: `1px solid var(--ok-green)`, color: 'var(--ok-green)',
          }}>
            {c.tier}
          </span>
          {c.open_to_work && (
            <span style={{
              fontFamily: 'Inter', fontSize: 10, fontWeight: 500,
              padding: '2px 7px', border: '1px solid var(--ok-green)', color: 'var(--ok-green)',
            }}>
              Open to Work
            </span>
          )}
        </div>
        <p style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--ink-faint)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {[c.current_title, c.current_company, c.location].filter(Boolean).join(' · ')}
        </p>
      </div>

      {/* Skills */}
      <div style={{ display: 'flex', gap: 5, flexShrink: 0 }}>
        {(c.top_skills || []).slice(0, 3).map(s => (
          <span key={s} style={{
            fontFamily: 'JetBrains Mono', fontSize: 9,
            border: '1px solid var(--rule)', color: 'var(--ink-faint)',
            padding: '2px 7px', letterSpacing: '-0.02em',
          }}>
            {s}
          </span>
        ))}
      </div>

      {/* Score */}
      <span style={{
        fontFamily: 'Fraunces', fontWeight: 700, fontSize: 22,
        color: 'var(--gold)', width: 52, textAlign: 'right', flexShrink: 0,
      }}>
        {score.toFixed(0)}
      </span>

      <span style={{ color: hovered ? 'var(--accent)' : 'var(--rule)', fontSize: 14, flexShrink: 0, transition: 'color 150ms ease' }}>
        →
      </span>
    </div>
  )
}

export default function Candidates({ candidates }) {
  const [query, setQuery] = useState('')
  const [tier, setTier] = useState('')
  const [mode, setMode] = useState('')
  const [selected, setSelected] = useState(null)

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    return candidates.filter(c => {
      const matchQ = !q || [c.name, c.current_title, c.current_company, ...(c.top_skills || [])].join(' ').toLowerCase().includes(q)
      const matchTier = !tier || c.tier === tier
      const matchMode = !mode || c.preferred_work_mode === mode
      return matchQ && matchTier && matchMode
    })
  }, [candidates, query, tier, mode])

  if (!candidates.length) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 320, gap: 14 }}>
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" opacity="0.25">
          <circle cx="20" cy="20" r="13" stroke="var(--ink)" strokeWidth="1.5" fill="none"/>
          <line x1="29" y1="29" x2="42" y2="42" stroke="var(--ink)" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
        <p style={{ fontFamily: 'Fraunces', fontStyle: 'italic', fontSize: 16, color: 'var(--ink-faint)' }}>
          Run a ranking first to see candidates here.
        </p>
      </div>
    )
  }

  if (selected) {
    return <CandidateProfile candidate={selected} onBack={() => setSelected(null)} />
  }

  return (
    <div>
      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 24, alignItems: 'center' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <svg width="13" height="13" viewBox="0 0 20 20" fill="none" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
            <circle cx="8" cy="8" r="5.5" stroke="var(--ink-faint)" strokeWidth="1.5"/>
            <line x1="12" y1="12" x2="17" y2="17" stroke="var(--ink-faint)" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Filter by name, title, skill…"
            style={{ ...inputBase, width: '100%', paddingLeft: 34, padding: '9px 12px 9px 34px' }}
            onFocus={e => e.target.style.borderColor = 'var(--gold)'}
            onBlur={e => e.target.style.borderColor = 'var(--rule)'}
          />
        </div>
        {[
          { val: tier, set: setTier, opts: [['', 'All Tiers'], ['A', 'Tier A'], ['B', 'Tier B'], ['C', 'Tier C']] },
          { val: mode, set: setMode, opts: [['', 'All Modes'], ['remote', 'Remote'], ['hybrid', 'Hybrid'], ['onsite', 'Onsite']] },
        ].map(({ val, set, opts }, i) => (
          <select
            key={i}
            value={val}
            onChange={e => set(e.target.value)}
            style={{ ...inputBase, padding: '9px 12px' }}
            onFocus={e => e.target.style.borderColor = 'var(--gold)'}
            onBlur={e => e.target.style.borderColor = 'var(--rule)'}
          >
            {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        ))}
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color: 'var(--ink-faint)', flexShrink: 0 }}>
          {filtered.length} results
        </span>
      </div>

      {/* Column header */}
      <div style={{ display: 'flex', gap: 18, padding: '0 24px 10px', borderBottom: '1px solid var(--rule)', marginBottom: 0 }}>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--ink-faint)', width: 48 }}>Rank</span>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--ink-faint)', flex: 1 }}>Candidate</span>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--ink-faint)' }}>Top Skills</span>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--ink-faint)', width: 52, textAlign: 'right' }}>Score</span>
        <span style={{ width: 22 }} />
      </div>

      {filtered.length === 0 ? (
        <p style={{ fontFamily: 'Fraunces', fontStyle: 'italic', fontSize: 15, color: 'var(--ink-faint)', textAlign: 'center', marginTop: 60 }}>
          No candidates match your filters.
        </p>
      ) : (
        <div>
          {filtered.map(c => (
            <CandidateRow key={c.candidate_id} c={c} onClick={setSelected} />
          ))}
        </div>
      )}
    </div>
  )
}
