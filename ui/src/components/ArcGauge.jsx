import { useEffect, useRef, useState } from 'react'

const R    = 38
const CX   = 50
const CY   = 50
const CIRC = 2 * Math.PI * R   // 238.76
const ARC  = CIRC * 0.75       // 270° arc = 179.07

export default function ArcGauge({ score }) {
  const pct = Math.min(Math.max(score, 0), 100)
  const [animated, setAnimated] = useState(0)
  const raf = useRef(null)

  useEffect(() => {
    let start = null
    const duration = 800
    function step(ts) {
      if (!start) start = ts
      const progress = Math.min((ts - start) / duration, 1)
      const ease = 1 - Math.pow(1 - progress, 3)
      setAnimated(pct * ease)
      if (progress < 1) raf.current = requestAnimationFrame(step)
    }
    raf.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf.current)
  }, [pct])

  const fillLen = (animated / 100) * ARC

  return (
    <svg width="100" height="100" viewBox="0 0 100 100">
      {/* Background track */}
      <circle
        cx={CX} cy={CY} r={R}
        fill="none"
        stroke="var(--rule)"
        strokeWidth="7"
        strokeDasharray={`${ARC} ${CIRC - ARC}`}
        transform="rotate(135 50 50)"
        strokeLinecap="butt"
      />
      {/* Filled arc */}
      <circle
        cx={CX} cy={CY} r={R}
        fill="none"
        stroke="var(--gold)"
        strokeWidth="7"
        strokeDasharray={`${fillLen} ${CIRC - fillLen}`}
        transform="rotate(135 50 50)"
        strokeLinecap="butt"
      />
      {/* Score number */}
      <text
        x="50" y="46"
        textAnchor="middle"
        dominantBaseline="middle"
        fill="var(--gold)"
        fontSize="20"
        fontWeight="900"
        fontFamily="Fraunces, serif"
      >
        {Math.round(animated)}
      </text>
      {/* /100 label */}
      <text
        x="50" y="61"
        textAnchor="middle"
        fill="var(--ink-faint)"
        fontSize="9"
        fontFamily="Inter, system-ui"
        fontWeight="400"
      >
        /100
      </text>
    </svg>
  )
}
