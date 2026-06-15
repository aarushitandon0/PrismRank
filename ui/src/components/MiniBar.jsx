import { useEffect, useRef, useState } from 'react'

export default function MiniBar({ label, value, delay = 0 }) {
  const pct = Math.round((value || 0) * 100)
  const [width, setWidth] = useState(0)
  const raf = useRef(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      let start = null
      const duration = 600
      function step(ts) {
        if (!start) start = ts
        const p = Math.min((ts - start) / duration, 1)
        const ease = 1 - Math.pow(1 - p, 3)
        setWidth(pct * ease)
        if (p < 1) raf.current = requestAnimationFrame(step)
      }
      raf.current = requestAnimationFrame(step)
    }, delay)
    return () => { clearTimeout(timer); cancelAnimationFrame(raf.current) }
  }, [pct, delay])

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7, minWidth: 0 }}>
      <span style={{
        fontFamily: 'JetBrains Mono', fontSize: 10,
        color: 'var(--ink-faint)',
        width: 60, flexShrink: 0,
        letterSpacing: '-0.02em',
      }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 3, background: 'var(--rule)', overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${width}%`,
          background: 'var(--gold)',
          transition: 'none',
        }} />
      </div>
      <span style={{
        fontFamily: 'Inter', fontSize: 10,
        color: 'var(--ink-faint)',
        width: 28, textAlign: 'right', flexShrink: 0,
      }}>
        {pct}%
      </span>
    </div>
  )
}
