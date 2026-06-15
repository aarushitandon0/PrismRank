import ArcGauge from './ArcGauge'
import MiniBar from './MiniBar'

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 28 }}>
      <p style={{
        fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase',
        letterSpacing: '0.14em', color: 'var(--ink-faint)', marginBottom: 12,
        paddingBottom: 8, borderBottom: '1px solid var(--rule)',
      }}>
        {title}
      </p>
      {children}
    </div>
  )
}

function Sentence({ children }) {
  return (
    <p style={{ fontFamily: 'Inter', fontSize: 14, color: 'var(--ink-muted)', lineHeight: 1.8, marginBottom: 8 }}>
      {children}
    </p>
  )
}

function ScorePill({ label, value }) {
  const pct = ((value || 0) * 100).toFixed(0)
  const color = pct >= 75 ? 'var(--ok-green)' : pct >= 50 ? 'var(--gold)' : 'var(--warn-orange)'
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--rule)',
      padding: '14px 18px', flex: 1,
    }}>
      <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--ink-faint)', marginBottom: 8 }}>
        {label}
      </p>
      <p style={{ fontFamily: 'Fraunces', fontWeight: 900, fontSize: 28, color, lineHeight: 1 }}>
        {pct}<span style={{ fontSize: 12, fontWeight: 300, color: 'var(--ink-faint)' }}>%</span>
      </p>
    </div>
  )
}

function buildNarrative(c) {
  const name = c.name || 'This candidate'
  const title = c.current_title || 'a professional'
  const company = c.current_company
  const yrs = c.years_experience
  const loc = [c.location, c.country].filter(Boolean).join(', ')
  const skills = c.top_skills || []
  const score = ((c.final_score || 0) * 100).toFixed(1)
  const tier = c.tier
  const mode = c.preferred_work_mode

  const overview = `${name} is ${yrs ? `a ${title} with ${yrs} year${yrs !== 1 ? 's' : ''} of experience` : `a ${title}`}${company ? `, currently working at ${company}` : ''}${loc ? `. Based in ${loc}` : ''}.`

  const skillsPara = skills.length
    ? `Their core technical expertise spans ${skills.slice(0, -1).join(', ')}${skills.length > 1 ? `, and ${skills[skills.length - 1]}` : skills[0]}.`
    : null

  const scorePara = `Across the AI evaluation pipeline, ${name.split(' ')[0]} received an overall score of ${score} out of 100, placing them at rank #${c.rank} in the shortlisted pool. They are classified as a Tier ${tier} candidate, ${tier === 'A' ? 'representing the top tier and a strong hiring recommendation' : tier === 'B' ? 'indicating a solid match with moderate gaps' : 'indicating a partial fit that warrants careful consideration'}.`

  const behaviorPara = (() => {
    const bits = []
    if (c.skill_alignment != null)  bits.push(`skill alignment of ${((c.skill_alignment || 0) * 100).toFixed(0)}%`)
    if (c.experience_fit != null)   bits.push(`experience fit of ${((c.experience_fit || 0) * 100).toFixed(0)}%`)
    if (c.behavioral_score != null) bits.push(`a behavioral score of ${((c.behavioral_score || 0) * 100).toFixed(0)}%`)
    if (c.culture_fit != null)      bits.push(`a culture fit of ${((c.culture_fit || 0) * 100).toFixed(0)}%`)
    return bits.length ? `The evaluation attributed them ${bits.join(', ')}.` : null
  })()

  const availability = (() => {
    const parts = []
    if (c.open_to_work) parts.push(`${name.split(' ')[0]} is actively open to new opportunities`)
    else parts.push(`${name.split(' ')[0]} is not currently marked as actively looking`)
    if (mode && mode !== 'any') parts.push(`and prefers ${mode} work arrangements`)
    if (c.trajectory_label) parts.push(`Their career trajectory is described as "${c.trajectory_label}"`)
    return parts.join('. ') + '.'
  })()

  return { overview, skillsPara, scorePara, behaviorPara, availability, alert: c.gap_alert, exceptional: c.exceptional_fit, summary: c.one_line_summary }
}

export default function CandidateProfile({ candidate: c, onBack }) {
  const score = (c.final_score || 0) * 100
  const n = buildNarrative(c)

  return (
    <div>
      {/* Back button */}
      <button
        onClick={onBack}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, marginBottom: 28,
          fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)',
          background: 'none', border: 'none', cursor: 'pointer', padding: 0,
          transition: 'color 150ms ease',
        }}
        onMouseEnter={e => e.currentTarget.style.color = 'var(--accent)'}
        onMouseLeave={e => e.currentTarget.style.color = 'var(--ink-muted)'}
      >
        ← Back to candidates
      </button>

      {/* Hero header */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--rule)',
        borderTop: '3px solid var(--accent)',
        padding: '30px 36px',
        display: 'flex', gap: 36,
        alignItems: 'flex-start', marginBottom: 28,
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8, flexWrap: 'wrap' }}>
            <h1 style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 34, color: 'var(--ink)', letterSpacing: '-0.02em', lineHeight: 1 }}>
              {c.name}
            </h1>
            <span style={{
              fontFamily: 'JetBrains Mono', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em',
              padding: '3px 9px', border: '1px solid var(--ok-green)', color: 'var(--ok-green)',
            }}>
              Tier {c.tier}
            </span>
            {c.exceptional_fit && (
              <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '3px 8px', border: '1px solid var(--accent)', color: 'var(--accent)' }}>
                Exceptional Fit
              </span>
            )}
          </div>

          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 18 }}>
            {c.current_title && (
              <span style={{ fontFamily: 'Inter', fontSize: 14, color: 'var(--ink-muted)' }}>
                {c.current_title}{c.current_company ? ` at ${c.current_company}` : ''}
              </span>
            )}
            {(c.location || c.country) && (
              <span style={{ fontFamily: 'Inter', fontSize: 14, color: 'var(--ink-faint)' }}>
                · {[c.location, c.country].filter(Boolean).join(', ')}
              </span>
            )}
            {c.years_experience != null && (
              <span style={{ fontFamily: 'Inter', fontSize: 14, color: 'var(--ink-faint)' }}>
                · {c.years_experience} years experience
              </span>
            )}
          </div>

          {/* Skills */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {(c.top_skills || []).map(s => (
              <span key={s} style={{
                fontFamily: 'JetBrains Mono', fontSize: 10,
                border: '1px solid var(--rule)',
                color: 'var(--ink-muted)', padding: '3px 10px', letterSpacing: '-0.02em',
              }}>
                {s}
              </span>
            ))}
            {c.open_to_work && (
              <span style={{
                fontFamily: 'Inter', fontSize: 10, fontWeight: 500,
                border: '1px solid var(--ok-green)',
                color: 'var(--ok-green)', padding: '3px 10px',
              }}>
                Open to Work
              </span>
            )}
          </div>
        </div>

        {/* Gauge + rank */}
        <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <ArcGauge score={score} />
          <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: 'var(--ink-faint)', textTransform: 'uppercase', letterSpacing: '0.10em' }}>
            Rank #{c.rank}
          </span>
        </div>
      </div>

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 28, alignItems: 'flex-start' }}>

        {/* Left: narrative */}
        <div>
          <Section title="Profile Overview">
            <Sentence>{n.overview}</Sentence>
            {n.summary && (
              <p style={{
                fontFamily: 'Fraunces', fontStyle: 'italic', fontWeight: 300,
                fontSize: 15, color: 'var(--ink)',
                borderLeft: '3px solid var(--accent)', paddingLeft: 16, lineHeight: 1.7,
                marginBottom: 8,
              }}>
                "{n.summary}"
              </p>
            )}
          </Section>

          {n.skillsPara && (
            <Section title="Technical Skills">
              <Sentence>{n.skillsPara}</Sentence>
            </Section>
          )}

          <Section title="Evaluation Summary">
            <Sentence>{n.scorePara}</Sentence>
            {n.behaviorPara && <Sentence>{n.behaviorPara}</Sentence>}
          </Section>

          <Section title="Availability & Work Style">
            <Sentence>{n.availability}</Sentence>
            {n.alert && (
              <div style={{ background: 'var(--warn-bg)', borderLeft: '3px solid var(--warn-orange)', padding: '10px 14px', marginTop: 8 }}>
                <p style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--warn-orange)', lineHeight: 1.6 }}>{n.alert}</p>
              </div>
            )}
          </Section>

          {n.exceptional && (
            <Section title="Exceptional Fit Signal">
              <Sentence>
                This candidate has been flagged as an exceptional fit by the LLM scoring stage — their profile closely aligns with the specific requirements and culture signals in the job description beyond what scores alone capture.
              </Sentence>
            </Section>
          )}
        </div>

        {/* Right: score breakdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Score cards */}
          <div>
            <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.14em', color: 'var(--ink-faint)', marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid var(--rule)' }}>
              Score Breakdown
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              <ScorePill label="Skill Alignment" value={c.skill_alignment}  />
              <ScorePill label="Experience Fit"  value={c.experience_fit}   />
              <ScorePill label="Behavioral"      value={c.behavioral_score} />
              <ScorePill label="Culture Fit"     value={c.culture_fit}      />
            </div>
          </div>

          {/* Mini bars */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--rule)', padding: '18px' }}>
            <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.14em', color: 'var(--ink-faint)', marginBottom: 14 }}>
              Signal Bars
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <MiniBar label="Skill"      value={c.skill_alignment}  delay={0}   />
              <MiniBar label="Experience" value={c.experience_fit}   delay={100} />
              <MiniBar label="Behavioral" value={c.behavioral_score} delay={200} />
              <MiniBar label="Culture"    value={c.culture_fit}      delay={300} />
            </div>
          </div>

          {/* Metadata */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--rule)', padding: '18px' }}>
            <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.14em', color: 'var(--ink-faint)', marginBottom: 12 }}>
              Metadata
            </p>
            {[
              ['Candidate ID', c.candidate_id],
              ['Work Mode',    c.preferred_work_mode || '—'],
              ['Trajectory',   c.trajectory_label || '—'],
              ['Cluster',      c.cluster_id != null ? `Persona #${c.cluster_id}` : '—'],
            ].filter(([, v]) => v).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingBottom: 8, marginBottom: 8, borderBottom: '1px solid var(--rule)' }}>
                <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: 'var(--ink-faint)' }}>{k}</span>
                <span style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--ink-muted)', textAlign: 'right', maxWidth: 160 }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
