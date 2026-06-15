import { useEffect, useState } from 'react'

export default function TopoBackground() {
  const [reducedMotion, setReducedMotion] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const h = e => setReducedMotion(e.matches)
    mq.addEventListener('change', h)
    return () => mq.removeEventListener('change', h)
  }, [])

  const lineCount = 24
  const lines = Array.from({ length: lineCount }, (_, i) => Math.round((i + 0.5) * (1100 / lineCount)))

  return (
    <svg
      aria-hidden="true"
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
        overflow: 'hidden',
      }}
      viewBox="0 0 1200 1100"
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <filter id="topo-warp" x="-25%" y="-25%" width="150%" height="150%">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.006 0.014"
            numOctaves="3"
            seed="7"
            result="noise"
          >
            {!reducedMotion && (
              <animate
                attributeName="baseFrequency"
                values="0.006 0.014;0.010 0.020;0.007 0.016;0.006 0.014"
                dur="55s"
                repeatCount="indefinite"
              />
            )}
          </feTurbulence>
          <feDisplacementMap
            in="SourceGraphic"
            in2="noise"
            scale="50"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </defs>
      <g
        filter="url(#topo-warp)"
        stroke="#8B6914"
        strokeWidth="1.1"
        fill="none"
        opacity="0.07"
      >
        {lines.map(y => (
          <line key={y} x1="-150" y1={y} x2="1350" y2={y} />
        ))}
      </g>
    </svg>
  )
}
