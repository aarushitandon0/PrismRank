const Sep = () => (
  <span style={{ width: 1, height: 20, background: 'var(--rule)', display: 'inline-block', margin: '0 18px', flexShrink: 0 }} />
)

function Stat({ label, value }) {
  return (
    <span style={{ display: 'flex', alignItems: 'baseline', gap: 5 }}>
      <span style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 15, color: 'var(--ink)' }}>{value}</span>
      <span style={{ fontFamily: 'Inter', fontWeight: 400, fontSize: 11, color: 'var(--ink-faint)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
    </span>
  )
}

export default function Header({ activeTab, rankingData }) {
  const candidates = rankingData?.shortlist || []
  const hasData = candidates.length > 0
  const topScore = hasData ? (candidates[0].final_score * 100).toFixed(1) : null
  const biasWarnings = hasData && rankingData?.bias_report && !rankingData.bias_report.audit_passed

  return (
    <header style={{
      position: 'sticky', top: 0, zIndex: 30,
      background: 'var(--bg-primary)',
      borderBottom: '1px solid var(--rule)',
      padding: '0 48px',
      height: 52,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      flexShrink: 0,
    }}>
      <span style={{
        fontFamily: 'Fraunces', fontWeight: 700, fontSize: 13,
        color: 'var(--ink)', letterSpacing: '-0.01em',
        textTransform: 'none',
      }}>
        {{
          dashboard:  'Dashboard',
          candidates: 'Candidates',
          personas:   'Talent Personas',
          bias:       'Bias Audit',
          interviews: 'Interview Packs',
          chat:       'Recruiter Chat',
        }[activeTab] || activeTab}
      </span>

      {hasData && (
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Stat value={(rankingData.total_candidates || 0).toLocaleString()} label="scanned" />
          <Sep />
          <Stat value={candidates.length} label="shortlisted" />
          <Sep />
          <Stat value={`${rankingData.processing_time_seconds}s`} label="" />
          <Sep />
          <Stat value={topScore} label="top score" />
          <Sep />

          {biasWarnings && (
            <>
              <span style={{
                fontFamily: 'Inter', fontSize: 11, fontWeight: 500,
                background: 'rgba(200,81,27,0.10)',
                border: '1px solid var(--warn-orange)',
                color: 'var(--warn-orange)',
                padding: '3px 10px', borderRadius: 12,
                marginRight: 14,
              }}>
                ⚠ Bias Warnings
              </span>
            </>
          )}

          <a
            href="/api/download/submission-csv"
            target="_blank"
            style={{
              fontFamily: 'Inter', fontSize: 11, fontWeight: 600,
              textTransform: 'uppercase', letterSpacing: '0.08em',
              color: 'var(--ink)', border: '1px solid var(--ink)', background: 'transparent',
              padding: '5px 14px', textDecoration: 'none',
              display: 'flex', alignItems: 'center', gap: 6,
              transition: 'background 150ms ease, color 150ms ease',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'var(--ink)'
              e.currentTarget.style.color = 'var(--bg-primary)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = 'var(--ink)'
            }}
          >
            Export CSV
          </a>
        </div>
      )}
    </header>
  )
}
