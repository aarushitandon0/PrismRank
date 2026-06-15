import { useState } from 'react'
import ArcGauge from './ArcGauge'
import MiniBar from './MiniBar'

function Tags({ skills = [], openToWork }) {
  const shown = skills.slice(0, 3)
  const extra = skills.length - shown.length
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, alignItems: 'center' }}>
      {shown.map(s => (
        <span key={s} style={{
          fontFamily: 'JetBrains Mono', fontSize: 10,
          background: 'transparent', border: '1px solid var(--rule)',
          color: 'var(--ink-muted)', padding: '2px 8px',
          letterSpacing: '-0.02em',
        }}>
          {s}
        </span>
      ))}
      {extra > 0 && (
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: 'var(--ink-faint)', padding: '2px 7px', border: '1px solid var(--rule)' }}>
          +{extra}
        </span>
      )}
      {openToWork && (
        <span style={{ fontFamily: 'Inter', fontSize: 10, fontWeight: 500, padding: '2px 8px', border: '1px solid var(--ok-green)', color: 'var(--ok-green)', background: 'transparent' }}>
          Open to Work
        </span>
      )}
    </div>
  )
}

function TrajBadge({ label }) {
  if (!label) return null
  const l = label.toLowerCase()
  const isRocket = l.includes('rocket')
  const isVet = l.includes('vet')
  return (
    <span style={{
      fontFamily: 'Inter', fontSize: 11, fontWeight: 500,
      color: isRocket ? 'var(--accent)' : isVet ? 'var(--ink-muted)' : 'var(--ok-green)',
    }}>
      {isRocket ? '↑↑' : isVet ? '◆' : '↑'} {label}
    </span>
  )
}

/* ── HERO CARD — Rank #1 ── */
function HeroCard({ c, delay }) {
  const score = (c.final_score || 0) * 100
  const barBase = delay + 400
  const [hov, setHov] = useState(false)
  return (
    <div
      className="card-in"
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: hov
          ? 'var(--bg-secondary)'
          : 'linear-gradient(135deg, var(--bg-card) 0%, var(--bg-primary) 100%)',
        border: '1px solid var(--rule)',
        borderLeft: '3px solid var(--accent)',
        padding: '32px 36px',
        display: 'flex', gap: 36, alignItems: 'flex-start',
        animationDelay: `${delay}ms`,
        transform: hov ? 'translateY(-2px)' : 'translateY(0)',
        boxShadow: hov ? '0 8px 28px rgba(44,24,16,0.10)' : '0 1px 4px rgba(44,24,16,0.04)',
        transition: 'transform 200ms ease, box-shadow 200ms ease, background 200ms ease',
        cursor: 'default',
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <span style={{
            fontFamily: 'Fraunces', fontWeight: 900, fontSize: 11,
            color: 'var(--ink-faint)', letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}>
            #1
          </span>
          <span style={{
            fontFamily: 'JetBrains Mono', fontSize: 9, letterSpacing: '0.06em',
            padding: '2px 6px', border: `1px solid var(--ok-green)`, color: 'var(--ok-green)',
            textTransform: 'uppercase',
          }}>
            {c.tier}
          </span>
          {c.exceptional_fit && (
            <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: 'var(--accent)', border: '1px solid var(--accent)', padding: '1px 6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Exceptional
            </span>
          )}
        </div>

        <h2 style={{
          fontFamily: 'Fraunces', fontWeight: 700, fontSize: 34,
          color: 'var(--ink)', letterSpacing: '-0.025em', lineHeight: 1.1,
          marginBottom: 4,
        }}>
          {c.name}
        </h2>
        <div style={{ height: 1, background: 'var(--rule)', margin: '10px 0' }} />

        <p style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)', marginBottom: 12 }}>
          {c.current_title}
          {c.current_company && <span style={{ color: 'var(--ink-faint)' }}> · {c.current_company}</span>}
          {c.location && <span style={{ color: 'var(--ink-faint)' }}> · {c.location}</span>}
          {c.years_experience != null && <span style={{ color: 'var(--ink-faint)' }}> · {c.years_experience}yr exp</span>}
        </p>

        {c.one_line_summary && (
          <p style={{
            fontFamily: 'Inter', fontSize: 13, fontStyle: 'italic',
            color: 'var(--ink-muted)', marginBottom: 16, lineHeight: 1.65,
            borderLeft: '2px solid var(--accent)', paddingLeft: 14,
          }}>
            "{c.one_line_summary}"
          </p>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          <Tags skills={c.top_skills} openToWork={c.open_to_work} />
          <TrajBadge label={c.trajectory_label} />
        </div>
      </div>

      <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, width: 160 }}>
        <ArcGauge score={score} />
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 7 }}>
          <MiniBar label="Skill"       value={c.skill_alignment}  delay={barBase}       />
          <MiniBar label="Experience"  value={c.experience_fit}   delay={barBase + 80}  />
          <MiniBar label="Behavioral"  value={c.behavioral_score} delay={barBase + 160} />
          <MiniBar label="Culture"     value={c.culture_fit}      delay={barBase + 240} />
        </div>
      </div>
    </div>
  )
}

/* ── MEDIUM CARD — Ranks #2-3 ── */
function MediumCard({ c, delay }) {
  const score = (c.final_score || 0) * 100
  const barBase = delay + 400
  const [hov, setHov] = useState(false)
  return (
    <div
      className="card-in"
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: hov ? 'var(--bg-secondary)' : 'var(--bg-card)',
        border: '1px solid var(--rule)',
        padding: '24px',
        display: 'flex', flexDirection: 'column', gap: 12,
        animationDelay: `${delay}ms`,
        transform: hov ? 'translateY(-2px)' : 'translateY(0)',
        boxShadow: hov ? '0 8px 24px rgba(44,24,16,0.10)' : '0 1px 4px rgba(44,24,16,0.04)',
        transition: 'transform 200ms ease, box-shadow 200ms ease, background 200ms ease',
        cursor: 'default',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', gap: 7, alignItems: 'center' }}>
          <span style={{
            fontFamily: 'Fraunces', fontWeight: 900, fontSize: 32,
            color: 'var(--rule)', lineHeight: 1,
          }}>
            {String(c.rank).padStart(2, '0')}
          </span>
          <span style={{
            fontFamily: 'JetBrains Mono', fontSize: 9, letterSpacing: '0.06em',
            padding: '2px 6px', border: `1px solid var(--ok-green)`, color: 'var(--ok-green)',
            textTransform: 'uppercase', alignSelf: 'center',
          }}>
            {c.tier}
          </span>
        </div>
        <span style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 26, color: 'var(--gold)', lineHeight: 1 }}>
          {score.toFixed(1)}
        </span>
      </div>

      <div>
        <h3 style={{
          fontFamily: 'Fraunces', fontWeight: 700, fontSize: 21,
          color: 'var(--ink)', letterSpacing: '-0.015em', marginBottom: 4,
        }}>
          {c.name}
        </h3>
        <div style={{ height: 1, background: 'var(--rule)', margin: '6px 0 8px' }} />
        <p style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--ink-muted)' }}>
          {c.current_title}
          {c.current_company && <span style={{ color: 'var(--ink-faint)' }}> · {c.current_company}</span>}
        </p>
      </div>

      <Tags skills={c.top_skills} openToWork={c.open_to_work} />
      <TrajBadge label={c.trajectory_label} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <MiniBar label="Skill"      value={c.skill_alignment}  delay={barBase}       />
        <MiniBar label="Experience" value={c.experience_fit}   delay={barBase + 80}  />
        <MiniBar label="Behavioral" value={c.behavioral_score} delay={barBase + 160} />
      </div>
    </div>
  )
}

/* ── LIST ROW — Ranks #4+ ── */
function ListRow({ c, delay }) {
  const score = (c.final_score || 0) * 100
  const [hov, setHov] = useState(false)
  return (
    <div
      className="card-in"
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: 16,
        padding: '14px 22px',
        background: hov ? 'var(--bg-secondary)' : 'var(--bg-card)',
        borderBottom: '1px solid var(--rule)',
        borderLeft: hov ? '3px solid var(--accent)' : '3px solid transparent',
        animationDelay: `${delay}ms`,
        transform: hov ? 'translateY(-1px)' : 'translateY(0)',
        boxShadow: hov ? '0 4px 14px rgba(44,24,16,0.07)' : 'none',
        transition: 'transform 200ms ease, box-shadow 200ms ease, background 150ms ease, border-left-color 150ms ease',
        cursor: 'default',
      }}
    >
      <span style={{
        fontFamily: 'Fraunces', fontWeight: 900, fontSize: 24,
        color: 'var(--rule)', width: 44, flexShrink: 0, lineHeight: 1,
      }}>
        {String(c.rank).padStart(2, '0')}
      </span>

      <div style={{ width: 220, flexShrink: 0 }}>
        <h4 style={{
          fontFamily: 'Fraunces', fontWeight: 700, fontSize: 16,
          color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          marginBottom: 2,
        }}>
          {c.name}
        </h4>
        <p style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--ink-faint)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {c.current_title}{c.current_company ? ` · ${c.current_company}` : ''}
        </p>
      </div>

      <div style={{ display: 'flex', gap: 5, flex: 1, flexWrap: 'wrap' }}>
        {(c.top_skills || []).slice(0, 3).map(s => (
          <span key={s} style={{
            fontFamily: 'JetBrains Mono', fontSize: 9,
            border: '1px solid var(--rule)', color: 'var(--ink-faint)',
            padding: '2px 6px', letterSpacing: '-0.02em',
          }}>
            {s}
          </span>
        ))}
        {(c.top_skills || []).length > 3 && (
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: 'var(--ink-faint)', padding: '2px 5px', border: '1px solid var(--rule)' }}>
            +{(c.top_skills || []).length - 3}
          </span>
        )}
      </div>

      {c.open_to_work && (
        <span style={{
          fontFamily: 'Inter', fontSize: 10, fontWeight: 500, flexShrink: 0,
          padding: '2px 7px', border: '1px solid var(--ok-green)', color: 'var(--ok-green)',
        }}>
          Open
        </span>
      )}

      <span style={{
        fontFamily: 'Fraunces', fontWeight: 700, fontSize: 18,
        color: 'var(--gold)', width: 44, textAlign: 'right', flexShrink: 0,
      }}>
        {score.toFixed(0)}
      </span>
    </div>
  )
}

export default function DashboardCard({ candidate: c, index }) {
  const delay = index === 0 ? 0 : index === 1 ? 60 : index === 2 ? 120 : 180 + (index - 3) * 30
  if (index === 0) return <HeroCard c={c} delay={delay} />
  if (index <= 2)  return <MediumCard c={c} delay={delay} />
  return <ListRow c={c} delay={delay} />
}
