interface KiroGhostProps {
  size?: number
  className?: string
}

/** Stand-in mark. The previous SVG was the Kiro ghost mascot.
 *  A real EFM logo is on the founder asset list. The export name stays.
 */
export function KiroGhost({ size = 40, className = '' }: KiroGhostProps) {
  const h = Math.round(size * 1.3)
  return (
    <svg width={size} height={h} viewBox="0 0 64 80" className={className} role="img" aria-label="EFM">
      <text x="32" y="50" textAnchor="middle" fill="currentColor" fontSize="20" fontFamily="sans-serif" fontWeight="700">EFM</text>
    </svg>
  )
}
