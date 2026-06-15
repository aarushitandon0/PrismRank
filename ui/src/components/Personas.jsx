const ACCENTS = ['var(--accent)', 'var(--gold)', 'var(--ok-green)', 'var(--ink-muted)', 'var(--warn-orange)']

function ProportionBar({ count, total, color }) {
  const pct = total > 0 ? (count / total) * 100 : 0
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: 'var(--rule)' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, transition: 'width 600ms ease' }} />
      </div>
      <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: 'var(--ink-faint)', width: 28, textAlign: 'right', flexShrink: 0 }}>
        {count}
      </span>
    </div>
  )
}

function ClusterId({ id }) {
  return (
    <span style={{
      fontFamily: 'Fraunces', fontWeight: 900, fontSize: 11,
      color: 'var(--ink-faint)', letterSpacing: '0.04em',
      background: 'var(--bg-secondary)', border: '1px solid var(--rule)',
      padding: '2px 7px',
    }}>
      C{id}
    </span>
  )
}

function SkillTags({ name }) {
  const words = (name || '').split(/[\s,–\-]+/).filter(w => w.length > 2 && w !== 'and' && w !== 'the').slice(0, 3)
  return (
    <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
      {words.map(w => (
        <span key={w} style={{
          fontFamily: 'JetBrains Mono', fontSize: 9,
          border: '1px solid var(--rule)', color: 'var(--ink-faint)',
          padding: '2px 7px', letterSpacing: '-0.02em',
        }}>
          {w}
        </span>
      ))}
    </div>
  )
}

function FeaturedCard({ c, accent, total }) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--rule)', borderLeft: `3px solid ${accent}`,
      padding: '24px 28px', display: 'flex', gap: 36, alignItems: 'center',
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <ClusterId id={c.id} />
          <h3 style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 20, color: 'var(--ink)', letterSpacing: '-0.01em' }}>
            {c.name}
          </h3>
        </div>
        <p style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)', lineHeight: 1.6, marginBottom: 12 }}>{c.description}</p>
        <SkillTags name={c.name} />
      </div>
      <div style={{ flexShrink: 0, width: 220 }}>
        <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--ink-faint)', marginBottom: 10 }}>
          {c.candidates.length} candidates · {((c.candidates.length / total) * 100).toFixed(0)}% of pool
        </p>
        <ProportionBar count={c.candidates.length} total={total} color={accent} />
        <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 5 }}>
          <p style={{ fontFamily: 'Inter', fontSize: 12 }}>
            <span style={{ color: 'var(--ok-green)', fontWeight: 500 }}>Strength: </span>
            <span style={{ color: 'var(--ink-muted)' }}>{c.strength}</span>
          </p>
          <p style={{ fontFamily: 'Inter', fontSize: 12 }}>
            <span style={{ color: 'var(--warn-orange)', fontWeight: 500 }}>Gap: </span>
            <span style={{ color: 'var(--ink-muted)' }}>{c.gap}</span>
          </p>
        </div>
      </div>
    </div>
  )
}

function MediumCard({ c, accent, total }) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--rule)',
      borderTop: `2px solid ${accent}`,
      padding: '20px 22px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <h4 style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 16, color: 'var(--ink)', letterSpacing: '-0.01em' }}>{c.name}</h4>
        <ClusterId id={c.id} />
      </div>
      <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--ink-faint)', marginBottom: 8 }}>
        {c.candidates.length} candidates
      </p>
      <ProportionBar count={c.candidates.length} total={total} color={accent} />
      <p style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--ink-muted)', lineHeight: 1.5, margin: '12px 0 10px' }}>{c.description}</p>
      <SkillTags name={c.name} />
      <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 4 }}>
        <p style={{ fontFamily: 'Inter', fontSize: 12 }}>
          <span style={{ color: 'var(--ok-green)', fontWeight: 500 }}>S: </span>
          <span style={{ color: 'var(--ink-muted)' }}>{c.strength}</span>
        </p>
        <p style={{ fontFamily: 'Inter', fontSize: 12 }}>
          <span style={{ color: 'var(--warn-orange)', fontWeight: 500 }}>G: </span>
          <span style={{ color: 'var(--ink-muted)' }}>{c.gap}</span>
        </p>
      </div>
    </div>
  )
}

function CompactCard({ c, accent, total }) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--rule)', borderLeft: `2px solid ${accent}`,
      padding: '16px 18px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <h5 style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 14, color: 'var(--ink)' }}>{c.name}</h5>
        <ClusterId id={c.id} />
      </div>
      <ProportionBar count={c.candidates.length} total={total} color={accent} />
      <p style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--ink-muted)', marginTop: 10 }}>
        <span style={{ color: 'var(--ok-green)', fontWeight: 500 }}>S: </span>{c.strength}
        <span style={{ color: 'var(--warn-orange)', fontWeight: 500, marginLeft: 10 }}>G: </span>{c.gap}
      </p>
    </div>
  )
}

export default function Personas({ personas }) {
  const clusters = [...(personas?.clusters || [])].sort((a, b) => b.candidates.length - a.candidates.length)
  const total = clusters.reduce((s, c) => s + c.candidates.length, 0)

  if (!clusters.length) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 320, gap: 14 }}>
        <svg width="44" height="44" viewBox="0 0 44 44" fill="none" opacity="0.25">
          <circle cx="10" cy="10" r="6" stroke="var(--ink)" strokeWidth="1.5" fill="none"/>
          <circle cx="34" cy="10" r="6" stroke="var(--ink)" strokeWidth="1.5" fill="none"/>
          <circle cx="22" cy="34" r="6" stroke="var(--ink)" strokeWidth="1.5" fill="none"/>
          <line x1="15" y1="13" x2="19" y2="29" stroke="var(--ink)" strokeWidth="1" opacity="0.5"/>
          <line x1="29" y1="13" x2="25" y2="29" stroke="var(--ink)" strokeWidth="1" opacity="0.5"/>
          <line x1="15" y1="10" x2="28" y2="10" stroke="var(--ink)" strokeWidth="1" opacity="0.5"/>
        </svg>
        <p style={{ fontFamily: 'Fraunces', fontStyle: 'italic', fontSize: 16, color: 'var(--ink-faint)' }}>
          Personas will appear after ranking.
        </p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 10 }}>
          <h2 style={{ fontFamily: 'Fraunces', fontWeight: 900, fontSize: 36, color: 'var(--ink)', letterSpacing: '-0.02em' }}>
            Talent Personas
          </h2>
          <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontFamily: 'Inter', fontSize: 12, color: 'var(--ok-green)' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--ok-green)' }} /> Strength
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontFamily: 'Inter', fontSize: 12, color: 'var(--warn-orange)' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--warn-orange)' }} /> Gap
            </span>
          </div>
        </div>
        <div style={{ height: 1, background: 'var(--rule)' }} />
        <p style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: 'var(--ink-faint)', marginTop: 8, letterSpacing: '-0.02em' }}>
          {clusters.length} clusters · {total} candidates mapped
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {clusters[0] && <FeaturedCard c={clusters[0]} accent={ACCENTS[0]} total={total} />}

        {clusters.length > 1 && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
            {clusters.slice(1, 3).map((c, i) => (
              <MediumCard key={c.id} c={c} accent={ACCENTS[i + 1]} total={total} />
            ))}
          </div>
        )}

        {clusters.length > 3 && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
            {clusters.slice(3).map((c, i) => (
              <CompactCard key={c.id} c={c} accent={ACCENTS[(i + 3) % ACCENTS.length]} total={total} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
