import { useState, useRef, useEffect } from 'react'

const QUICK = [
  'Python engineers with 5+ years',
  'Who has the strongest trajectory?',
  'Open to work and willing to relocate',
  'Tier A candidates only',
  'Remote candidates with high scores',
  'Rocket trajectory candidates',
]

function MiniCandidateRow({ c }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--rule)' }}>
      <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: 'var(--ink-faint)', width: 28, flexShrink: 0 }}>#{c.rank}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 14, color: 'var(--ink)' }}>{c.name}</p>
        <p style={{ fontFamily: 'Inter', fontSize: 12, color: 'var(--ink-faint)' }}>
          {c.current_title}{c.years_experience ? ` · ${c.years_experience}yr` : ''}
        </p>
      </div>
      <span style={{
        fontFamily: 'JetBrains Mono', fontSize: 9, textTransform: 'uppercase',
        padding: '2px 6px', border: '1px solid var(--ok-green)', color: 'var(--ok-green)',
      }}>
        {c.tier}
      </span>
      <span style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 16, color: 'var(--gold)', flexShrink: 0 }}>
        {(c.final_score * 100).toFixed(1)}
      </span>
    </div>
  )
}

const MapSearchIcon = () => (
  <svg width="52" height="52" viewBox="0 0 52 52" fill="none" opacity="0.25">
    <circle cx="22" cy="22" r="13" stroke="var(--ink)" strokeWidth="1.5" fill="none"/>
    <line x1="31" y1="31" x2="45" y2="45" stroke="var(--ink)" strokeWidth="1.5" strokeLinecap="round"/>
    <path d="M 14,22 Q 18,17 22,22 Q 26,27 30,22" stroke="var(--ink)" strokeWidth="1" fill="none" strokeLinecap="round"/>
    <path d="M 14,26 Q 18,21 22,26 Q 26,31 30,26" stroke="var(--ink)" strokeWidth="1" fill="none" strokeLinecap="round" opacity="0.5"/>
  </svg>
)

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  async function send(q) {
    if (!q.trim() || loading) return
    const query = q.trim()
    setInput('')
    setMessages(m => [...m, { type: 'user', text: query }])
    setLoading(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: 6 }),
      })
      const data = await res.json()
      setMessages(m => [...m, { type: 'ai', data }])
    } catch (err) {
      setMessages(m => [...m, { type: 'error', text: err.message }])
    }
    setLoading(false)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 140px)' }}>
      {/* Quick search pills */}
      <div style={{ marginBottom: 20 }}>
        <p style={{ fontFamily: 'JetBrains Mono', fontSize: 9, color: 'var(--ink-faint)', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 10 }}>
          Quick searches
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
          {QUICK.map(q => (
            <button
              key={q}
              onClick={() => send(q)}
              style={{
                fontFamily: 'JetBrains Mono', fontSize: 11,
                padding: '6px 13px',
                background: 'transparent', border: '1px solid var(--rule)',
                color: 'var(--ink-muted)', cursor: 'pointer',
                transition: 'all 150ms ease',
                letterSpacing: '-0.02em',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'var(--accent)'
                e.currentTarget.style.borderColor = 'var(--accent)'
                e.currentTarget.style.color = 'var(--bg-primary)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.borderColor = 'var(--rule)'
                e.currentTarget.style.color = 'var(--ink-muted)'
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Message area */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14, paddingBottom: 8 }}>
        {messages.length === 0 && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 14 }}>
            <MapSearchIcon />
            <p style={{ fontFamily: 'Fraunces', fontStyle: 'italic', fontSize: 18, color: 'var(--ink-faint)' }}>
              Ask anything about your talent pool.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className="animate-msg-in" style={{ display: 'flex', justifyContent: msg.type === 'user' ? 'flex-end' : 'flex-start' }}>
            {msg.type === 'user' && (
              <div style={{
                maxWidth: 440,
                background: 'var(--accent)',
                padding: '12px 18px',
              }}>
                <p style={{ fontFamily: 'Fraunces', fontStyle: 'italic', fontWeight: 300, fontSize: 15, color: 'var(--bg-primary)', lineHeight: 1.5 }}>
                  {msg.text}
                </p>
              </div>
            )}
            {msg.type === 'ai' && (
              <div style={{
                maxWidth: 660, width: '100%',
                background: 'var(--bg-card)', border: '1px solid var(--rule)',
                padding: '16px 20px',
              }}>
                <p style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: 'var(--ink-faint)', marginBottom: 12, letterSpacing: '-0.02em' }}>
                  Filter: {msg.data.filter_applied || 'semantic match'} — {msg.data.results?.length || 0} result(s)
                </p>
                {!msg.data.results?.length
                  ? <p style={{ fontFamily: 'Fraunces', fontStyle: 'italic', fontSize: 14, color: 'var(--ink-faint)' }}>No candidates matched. Try different criteria.</p>
                  : <div>{msg.data.results.map(c => <MiniCandidateRow key={c.candidate_id} c={c} />)}</div>
                }
              </div>
            )}
            {msg.type === 'error' && (
              <div style={{ padding: '10px 16px', background: 'var(--warn-bg)', borderLeft: '3px solid var(--warn-orange)' }}>
                <p style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--warn-orange)' }}>{msg.text}</p>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', gap: 6, padding: '10px 16px', background: 'var(--bg-card)', border: '1px solid var(--rule)', width: 'fit-content', alignItems: 'center' }}>
            {[0,1,2].map(i => (
              <span key={i} style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--gold)', display: 'block', animation: `pulse-dot 1s ease-in-out ${i*0.2}s infinite` }} />
            ))}
            <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: 'var(--ink-faint)', marginLeft: 6 }}>Searching…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: 8, paddingTop: 14, borderTop: '1px solid var(--rule)', marginTop: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send(input)}
          placeholder="Ask anything about your talent pool…"
          style={{
            flex: 1, background: 'var(--bg-card)', border: '2px solid var(--rule)',
            color: 'var(--ink)', padding: '11px 16px',
            fontFamily: 'Inter', fontSize: 13,
            transition: 'border-color 150ms ease',
          }}
          onFocus={e => e.target.style.borderColor = 'var(--ink)'}
          onBlur={e => e.target.style.borderColor = 'var(--rule)'}
        />
        <button
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          style={{
            background: 'var(--accent)', color: 'var(--bg-primary)',
            border: 'none', padding: '11px 22px',
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            fontFamily: 'Inter', fontWeight: 600, fontSize: 13,
            opacity: loading || !input.trim() ? 0.4 : 1,
            transition: 'background 150ms ease, opacity 150ms ease',
          }}
          onMouseEnter={e => { if (!loading && input.trim()) e.currentTarget.style.background = 'var(--accent-hover)' }}
          onMouseLeave={e => e.currentTarget.style.background = 'var(--accent)'}
        >
          Send
        </button>
      </div>
    </div>
  )
}
