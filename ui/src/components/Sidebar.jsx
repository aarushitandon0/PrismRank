const NAV = [
  { id: 'dashboard',  label: 'Dashboard'      },
  { id: 'candidates', label: 'Candidates'      },
  { id: 'personas',   label: 'Personas'        },
  { id: 'bias',       label: 'Bias Audit'      },
  { id: 'interviews', label: 'Interview Packs' },
  { id: 'chat',       label: 'Recruiter Chat'  },
]

const PrismMark = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <polygon points="10,2 18,17 2,17" fill="none" stroke="#E8440A" strokeWidth="1.2" strokeLinejoin="round"/>
    <polygon points="10,2 18,17 10,12" fill="#E8440A" opacity="0.30"/>
    <polygon points="10,2 2,17 10,12"  fill="#E8440A" opacity="0.14"/>
    <polygon points="2,17 18,17 10,12" fill="#E8440A" opacity="0.07"/>
    <line x1="10" y1="2" x2="10" y2="12" stroke="#E8440A" strokeWidth="0.8" opacity="0.55"/>
  </svg>
)

export default function Sidebar({ activeTab, onTabChange }) {
  return (
    <aside style={{
      position: 'fixed', left: 0, top: 0, bottom: 0, width: 220,
      background: 'var(--sidebar-bg)',
      display: 'flex', flexDirection: 'column', zIndex: 40,
    }}>
      {/* Logo block */}
      <div style={{ padding: '28px 22px 22px', borderBottom: '1px solid rgba(245,236,215,0.10)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <PrismMark />
          <span style={{
            fontFamily: 'Fraunces', fontWeight: 700, fontSize: 22,
            color: 'var(--sidebar-text)', letterSpacing: '-0.02em',
          }}>
            PrismRank
          </span>
        </div>
        <p style={{
          fontFamily: 'Inter', fontWeight: 400, fontSize: 10,
          color: 'rgba(245,236,215,0.45)',
          textTransform: 'uppercase', letterSpacing: '0.14em',
          paddingLeft: 30,
        }}>
          See every dimension of talent.
        </p>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '14px 0', display: 'flex', flexDirection: 'column' }}>
        {NAV.map(({ id, label }) => {
          const active = activeTab === id
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                height: 42, padding: '0 22px',
                background: active ? 'rgba(232,68,10,0.12)' : 'transparent',
                color: active ? '#F5ECD7' : 'rgba(245,236,215,0.50)',
                cursor: 'pointer', border: 'none',
                borderLeft: active ? '3px solid #E8440A' : '3px solid transparent',
                width: '100%', textAlign: 'left',
                transition: 'color 150ms ease, background 150ms ease, border-left-color 150ms ease',
                fontFamily: 'Inter', fontWeight: active ? 600 : 500, fontSize: 13,
              }}
              onMouseEnter={e => {
                if (!active) {
                  e.currentTarget.style.color = 'rgba(245,236,215,0.85)'
                  e.currentTarget.style.background = 'rgba(245,236,215,0.05)'
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  e.currentTarget.style.color = 'rgba(245,236,215,0.50)'
                  e.currentTarget.style.background = 'transparent'
                }
              }}
            >
              <span style={{
                width: 5, height: 5, borderRadius: '50%', flexShrink: 0,
                background: active ? '#E8440A' : 'rgba(245,236,215,0.25)',
                transition: 'background 150ms ease',
              }} />
              {label}
            </button>
          )
        })}
      </nav>

      {/* Status */}
      <div style={{
        padding: '16px 22px',
        borderTop: '1px solid rgba(245,236,215,0.10)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span
          className="animate-pulse-dot"
          style={{ width: 7, height: 7, borderRadius: '50%', background: '#4A7C59', flexShrink: 0, display: 'block' }}
        />
        <span style={{ fontFamily: 'Inter', fontSize: 12, color: 'rgba(245,236,215,0.40)' }}>
          API Connected
        </span>
      </div>
    </aside>
  )
}
