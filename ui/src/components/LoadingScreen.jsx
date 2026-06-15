import { useEffect, useState } from 'react'

const MSGS = [
  'Parsing resumes…',
  'Building semantic index…',
  'Running FAISS vector search…',
  'Scoring candidates with Gemini…',
  'Fusing behavioral signals…',
  'Clustering talent personas…',
  'Running bias audit…',
  'Generating interview packs…',
  'Finalizing rankings…',
]

const PrismSpinner = () => (
  <svg className="animate-spin-slow" width="72" height="72" viewBox="0 0 72 72" fill="none">
    <polygon points="36,6 64,58 8,58" fill="none" stroke="var(--rule)" strokeWidth="1.5" strokeLinejoin="round"/>
    <polygon points="36,6 64,58 36,42"  fill="var(--accent)"  opacity="0.28"/>
    <polygon points="36,6 8,58  36,42"  fill="var(--gold)"    opacity="0.18"/>
    <polygon points="8,58 64,58 36,42"  fill="var(--accent)"  opacity="0.08"/>
    <line x1="36" y1="6" x2="36" y2="42" stroke="var(--accent)" strokeWidth="1" opacity="0.55"/>
    <polygon points="36,6 64,58 8,58" fill="none" stroke="var(--accent)" strokeWidth="1.2" strokeLinejoin="round" opacity="0.55"/>
  </svg>
)

export default function LoadingScreen({ message }) {
  const [msgIdx, setMsgIdx] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setMsgIdx(i => (i + 1) % MSGS.length), 3000)
    return () => clearInterval(t)
  }, [])

  return (
    <div style={{
      position: 'fixed', inset: 0, left: 220, zIndex: 50,
      background: 'var(--bg-primary)',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 32,
    }}>
      <PrismSpinner />

      <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center' }}>
        <p style={{ fontFamily: 'Fraunces', fontWeight: 700, fontSize: 22, color: 'var(--ink)' }}>
          Mapping your talent pool
        </p>

        <div style={{ width: 260, height: 2, background: 'var(--rule)', overflow: 'hidden' }}>
          <div className="shimmer-bar" style={{ height: '100%', width: '100%' }} />
        </div>

        <p
          key={msgIdx}
          className="animate-fade-up"
          style={{ fontFamily: 'Inter', fontSize: 13, color: 'var(--ink-faint)' }}
        >
          {MSGS[msgIdx]}
        </p>
      </div>
    </div>
  )
}
