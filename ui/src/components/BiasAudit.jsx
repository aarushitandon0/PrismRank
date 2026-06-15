import { useEffect, useRef, useState } from 'react'

function AnimatedBar({ pct, color, delay = 0 }) {
  const [w, setW] = useState(0)
  const raf = useRef(null)
  useEffect(() => {
    const t = setTimeout(() => {
      let start = null
      function step(ts) {
        if (!start) start = ts
        const p = Math.min((ts - start) / 500, 1)
        setW(pct * (1 - Math.pow(1 - p, 2)))
        if (p < 1) raf.current = requestAnimationFrame(step)
      }
      raf.current = requestAnimationFrame(step)
    }, delay)
    return () => { clearTimeout(t); cancelAnimationFrame(raf.current) }
  }, [pct, delay])
  return (
    <div style={{ flex: 1, height: 6, background: 'var(--rule)', overflow: 'hidden' }}>
      <div style={{ height: '100%', width: `${w}%`, background: color }} />
    </div>
  )
}

function DualBar({ shortlist, pool }) {
  const s = (shortlist || 0) * 100
  const p = (pool || 0) * 100
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5, minWidth: 180 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: 'var(--gold)', width: 18, flexShrink: 0 }}>SL</span>
        <AnimatedBar pct={s} color="var(--gold)" delay={100} />
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: 'var(--gold)', width: 34, textAlign: 'right', flexShrink: 0 }}>{s.toFixed(0)}%</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: 'var(--ink-faint)', width: 18, flexShrink: 0 }}>PL</span>
        <AnimatedBar pct={p} color="var(--rule)" delay={200} />
        <span style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: 'var(--ink-faint)', width: 34, textAlign: 'right', flexShrink: 0 }}>{p.toFixed(0)}%</span>
      </div>
    </div>
  )
}

function SkewCell({ val }) {
  if (val === '—' || val == null) return <span style={{ fontFamily: 'Inter', fontSize: 14, color: 'var(--ink-faint)' }}>—</span>
  const n = parseFloat(val)
  if (n >= 2.0) return <span style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 22, color: 'var(--warn-orange)' }}>{n.toFixed(2)}</span>
  if (n >= 1.3) return <span style={{ fontFamily: 'Fraunces', fontWeight: 600, fontSize: 18, color: 'var(--gold)' }}>{n.toFixed(2)}</span>
  return <span style={{ fontFamily: 'Inter', fontSize: 14, color: 'var(--ink-muted)' }}>{n.toFixed(2)}</span>
}

function StatusBadge({ warn }) {
  return (
    <span style={{
      fontFamily: 'Inter', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em',
      padding: '4px 12px',
      background: warn ? 'var(--warn-bg)' : 'var(--ok-bg)',
      border: `1px solid ${warn ? 'var(--warn-orange)' : 'var(--ok-green)'}`,
      color: warn ? 'var(--warn-orange)' : 'var(--ok-green)',
    }}>
      {warn ? 'Warning' : 'OK'}
    </span>
  )
}

function HighlightNumbers({ text }) {
  const parts = text.split(/(\d+\.?\d*(?:%|x)?)/)
  return (
    <>
      {parts.map((part, i) =>
        /^\d+\.?\d*(?:%|x)?$/.test(part)
          ? <strong key={i} style={{ color: 'var(--warn-orange)', fontWeight: 600 }}>{part}</strong>
          : part
      )}
    </>
  )
}

function WarningAccordion({ text, i }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{
      background: '#FDF0E0',
      borderLeft: '4px solid var(--warn-orange)',
      marginBottom: 6,
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 12,
          padding: '13px 16px', background: 'none', border: 'none', cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <span style={{ fontFamily: 'Inter', fontSize: 12, fontWeight: 500, color: 'var(--warn-orange)', flexShrink: 0 }}>⚠</span>
        <p style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)', lineHeight: 1.5, flex: 1 }}>
          <HighlightNumbers text={text} />
        </p>
        <span style={{ color: 'var(--ink-faint)', fontSize: 12, flexShrink: 0, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 250ms ease' }}>▼</span>
      </button>
      {open && (
        <div style={{ padding: '0 16px 14px 40px', borderTop: '1px solid rgba(200,81,27,0.15)' }}>
          <p style={{ fontFamily: 'Inter', fontSize: 12, fontStyle: 'italic', color: 'var(--ink-faint)', marginTop: 10, lineHeight: 1.6 }}>
            This metric may indicate disproportionate filtering across demographic groups. Review hiring criteria for potential unintentional bias.
          </p>
        </div>
      )}
    </div>
  )
}

export default function BiasAudit({ report }) {
  if (!report) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 320, gap: 14 }}>
        <svg width="44" height="44" viewBox="0 0 44 44" fill="none" opacity="0.25">
          <rect x="4" y="28" width="8" height="12" stroke="var(--ink)" strokeWidth="1.5" fill="none"/>
          <rect x="18" y="18" width="8" height="22" stroke="var(--ink)" strokeWidth="1.5" fill="none"/>
          <rect x="32" y="10" width="8" height="30" stroke="var(--ink)" strokeWidth="1.5" fill="none"/>
        </svg>
        <p style={{ fontFamily: 'Fraunces', fontStyle: 'italic', fontSize: 16, color: 'var(--ink-faint)' }}>
          Run ranking first to see the bias audit.
        </p>
      </div>
    )
  }

  const passed = report.audit_passed
  const warnings = report.warnings || []
  const metrics = Object.entries(report.metrics || {})
  const warnCount = metrics.filter(([, v]) => v.warning).length
  const okCount = metrics.filter(([, v]) => !v.warning).length

  return (
    <div style={{ maxWidth: 980 }}>
      {/* Section heading */}
      <div style={{ marginBottom: 28 }}>
        <h2 style={{ fontFamily: 'Fraunces', fontWeight: 900, fontSize: 36, color: 'var(--ink)', letterSpacing: '-0.02em', marginBottom: 10 }}>
          Bias Audit
        </h2>
        <div style={{ height: 1, background: 'var(--rule)' }} />
      </div>

      {/* Status banner */}
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: 14, padding: '16px 20px',
        background: passed ? 'var(--ok-bg)' : '#FDF0E0',
        borderLeft: `4px solid ${passed ? 'var(--ok-green)' : 'var(--warn-orange)'}`,
        marginBottom: 20,
      }}>
        <div>
          <p style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 16, color: passed ? 'var(--ok-green)' : 'var(--warn-orange)' }}>
            {passed ? 'Bias Audit Passed' : 'Bias Warnings Detected'}
          </p>
          <p style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)', marginTop: 2 }}>
            {warnings.length} warning(s) found across demographic dimensions
          </p>
        </div>
      </div>

      {/* Warning accordions */}
      {warnings.map((w, i) => <WarningAccordion key={i} text={w} i={i} />)}

      {/* Metrics table */}
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--rule)',
        marginTop: warnings.length ? 24 : 0,
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Dimension', 'Shortlist', 'Pool', 'Skew Ratio', 'Bars', 'Status'].map(h => (
                <th key={h} style={{
                  padding: '13px 18px', textAlign: 'left',
                  fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase',
                  letterSpacing: '0.12em', color: 'var(--ink-faint)',
                  borderBottom: '1px solid var(--rule)', fontWeight: 400,
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map(([key, val]) => {
              const warn = val.warning
              const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
              const ssl = val.shortlist_share !== undefined ? `${(val.shortlist_share * 100).toFixed(1)}%` : val.shortlist_gini?.toFixed(3) ?? '—'
              const spl = val.pool_share !== undefined ? `${(val.pool_share * 100).toFixed(1)}%` : val.description ?? '—'
              const skew = val.skew_ratio ?? val.exclusion_skew_under3 ?? null
              const hasBars = val.shortlist_share !== undefined && val.pool_share !== undefined
              return (
                <tr
                  key={key}
                  style={{ borderBottom: '1px solid var(--rule)', transition: 'background 150ms ease', background: 'transparent' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-secondary)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ padding: '16px 18px' }}>
                    <span style={{ fontFamily: 'Fraunces', fontWeight: 600, fontSize: 15, color: 'var(--ink)' }}>{label}</span>
                  </td>
                  <td style={{ padding: '16px 18px', fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)', textAlign: 'center' }}>{ssl}</td>
                  <td style={{ padding: '16px 18px', fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-muted)', textAlign: 'center' }}>{spl}</td>
                  <td style={{ padding: '16px 18px', textAlign: 'center' }}>
                    <SkewCell val={skew} />
                  </td>
                  <td style={{ padding: '16px 18px' }}>
                    {hasBars ? <DualBar shortlist={val.shortlist_share} pool={val.pool_share} /> : <span style={{ color: 'var(--ink-faint)', fontSize: 11 }}>—</span>}
                  </td>
                  <td style={{ padding: '16px 18px', textAlign: 'center' }}>
                    <StatusBadge warn={warn} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <div style={{ padding: '12px 18px', borderTop: '1px solid var(--rule)' }}>
          <p style={{ fontFamily: 'Inter', fontSize: 12, fontStyle: 'italic', color: 'var(--ink-faint)' }}>
            {warnCount} warning{warnCount !== 1 ? 's' : ''} · {okCount} OK{report.recommendation ? ` · ${report.recommendation}` : ''}
          </p>
        </div>
      </div>
    </div>
  )
}
