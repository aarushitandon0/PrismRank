import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import ArcGauge from './ArcGauge'
import MiniBar from './MiniBar'

function TierBadge({ tier }) {
  const color = tier === 'A' ? 'var(--ok)' : tier === 'B' ? 'var(--text-muted)' : 'var(--text-faint)'
  return (
    <span style={{
      fontFamily: 'Fira Code', fontSize: 11, textTransform: 'uppercase',
      padding: '2px 6px', border: `1px solid ${color}`, color,
      borderRadius: 4, letterSpacing: '0.04em', flexShrink: 0,
    }}>
      {tier}
    </span>
  )
}

function Tag({ children, color }) {
  return (
    <span style={{
      fontFamily: 'Fira Code', fontSize: 11,
      background: 'var(--bg-raised)', border: `1px solid ${color || 'var(--border)'}`,
      color: color || 'var(--text-muted)',
      padding: '3px 8px', borderRadius: 4,
    }}>
      {children}
    </span>
  )
}

export default function CandidateCard({ candidate: c }) {
  const [open, setOpen] = useState(false)
  const [questions, setQuestions] = useState(null)
  const [loadingQ, setLoadingQ] = useState(false)
  const score = (c.final_score || 0) * 100

  async function toggle() {
    setOpen(o => !o)
    if (!open && !questions) {
      setLoadingQ(true)
      try {
        const res = await fetch('/api/download/interview-pack')
        if (res.ok) {
          const packs = await res.json()
          const pack = packs.find(p => p.candidate_id === c.candidate_id)
          setQuestions(pack?.questions || [])
        } else setQuestions([])
      } catch { setQuestions([]) }
      setLoadingQ(false)
    }
  }

  return (
    <div
      className="animate-fade-up"
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderLeft: '2px solid var(--border)',
        padding: '20px 24px',
        display: 'flex', gap: 24, alignItems: 'flex-start',
        transition: 'background 150ms ease, border-color 150ms ease',
        cursor: 'default',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = 'var(--bg-raised)'
        e.currentTarget.style.borderLeftColor = 'var(--border-accent)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = 'var(--bg-surface)'
        e.currentTarget.style.borderLeftColor = 'var(--border)'
      }}
    >
      {/* Rank */}
      <div style={{ width: 48, flexShrink: 0, paddingTop: 4 }}>
        <span style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 26, color: 'var(--text-faint)', display: 'block', lineHeight: 1 }}>
          #{c.rank}
        </span>
      </div>

      {/* Center */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Name + tier */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 4 }}>
          <span style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 18, color: 'var(--text-primary)' }}>
            {c.name}
          </span>
          <TierBadge tier={c.tier} />
          {c.exceptional_fit && <Tag color="var(--accent-dim)">Exceptional</Tag>}
        </div>

        {/* Role & company */}
        <p style={{ fontFamily: 'Plus Jakarta Sans', fontSize: 13, color: 'var(--text-muted)', marginBottom: 2 }}>
          {c.current_title} · {c.current_company}
        </p>

        {/* Location & exp */}
        <p style={{ fontFamily: 'Plus Jakarta Sans', fontSize: 12, color: 'var(--text-faint)', marginBottom: 8 }}>
          {c.location}{c.country ? `, ${c.country}` : ''} · {c.years_experience}yr exp
        </p>

        {/* Summary quote */}
        {c.one_line_summary && (
          <p style={{
            fontFamily: 'Plus Jakarta Sans', fontSize: 13, fontStyle: 'italic', color: 'var(--text-muted)',
            borderLeft: '2px solid var(--border-accent)', paddingLeft: 12, marginBottom: 12,
          }}>
            {c.one_line_summary}
          </p>
        )}

        {/* Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
          {(c.top_skills || []).slice(0, 5).map(s => <Tag key={s}>{s}</Tag>)}
          {c.open_to_work && <Tag color="var(--ok)">Open to Work</Tag>}
          {c.trajectory_label && <Tag color="var(--accent-dim)">{c.trajectory_label}</Tag>}
          {c.preferred_work_mode && c.preferred_work_mode !== 'any' && <Tag>{c.preferred_work_mode}</Tag>}
          {c.gap_alert && <Tag color="var(--warning)">{c.gap_alert.slice(0, 40)}</Tag>}
        </div>

        {/* Interview toggle */}
        <button
          onClick={toggle}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            fontFamily: 'Plus Jakarta Sans', fontSize: 12, color: 'var(--text-faint)',
            background: 'none', border: 'none', cursor: 'pointer',
            padding: 0, transition: 'color 150ms ease',
          }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--accent)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--text-faint)'}
        >
          <ChevronDown size={13} style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 200ms ease' }} />
          Interview questions
        </button>

        {open && (
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {loadingQ ? (
              <p style={{ fontFamily: 'Plus Jakarta Sans', fontSize: 12, color: 'var(--text-faint)' }}>Loading...</p>
            ) : questions?.length ? questions.map((q, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', flexShrink: 0, marginTop: 5 }} />
                <div>
                  <p style={{ fontFamily: 'Fira Code', fontSize: 10, color: 'var(--accent-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 3 }}>
                    {q.type}
                  </p>
                  <p style={{ fontFamily: 'Plus Jakarta Sans', fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.5 }}>{q.question}</p>
                  <p style={{ fontFamily: 'Plus Jakarta Sans', fontSize: 12, color: 'var(--text-faint)', fontStyle: 'italic', marginTop: 3 }}>
                    Listen for: {q.what_to_listen_for}
                  </p>
                </div>
              </div>
            )) : (
              <p style={{ fontFamily: 'Plus Jakarta Sans', fontSize: 12, color: 'var(--text-faint)' }}>No interview pack for this candidate.</p>
            )}
          </div>
        )}
      </div>

      {/* Right: Gauge + mini bars */}
      <div style={{ flexShrink: 0, width: 140, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
        <ArcGauge score={score} />
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 5 }}>
          <MiniBar label="Skill"       value={c.skill_alignment}  delay={0}   />
          <MiniBar label="Experience"  value={c.experience_fit}   delay={100} />
          <MiniBar label="Behavioral"  value={c.behavioral_score} delay={200} />
          <MiniBar label="Culture"     value={c.culture_fit}      delay={300} />
        </div>
      </div>
    </div>
  )
}
