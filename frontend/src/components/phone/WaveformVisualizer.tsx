import { useEffect, useMemo } from 'react'
import { clsx } from 'clsx'
import { ensureAnimStyles } from './phone-anim-styles'

interface Props {
  active: boolean
  barCount?: number
  color?: string
  height?: number
  className?: string
}

/**
 * Animated waveform visualizer. When `active`, bars animate with staggered
 * delays producing a realistic audio-waveform look. When inactive, bars
 * sit at random static heights.
 */
export default function WaveformVisualizer({
  active,
  barCount = 16,
  color = '#17C5B0',
  height = 24,
  className,
}: Props) {
  useEffect(() => { ensureAnimStyles() }, [])

  // Generate stable random heights for the static (inactive) state.
  const staticHeights = useMemo(
    () => Array.from({ length: barCount }, () => 3 + Math.random() * (height * 0.6)),
    [barCount, height],
  )

  return (
    <div
      className={clsx('flex items-end justify-center gap-[2px]', className)}
      style={{ height }}
    >
      {Array.from({ length: barCount }).map((_, i) => (
        <div
          key={i}
          className={clsx(
            'rounded-full transition-all duration-200',
            active && 'wave-bar',
          )}
          style={{
            width: barCount > 12 ? 2 : 3,
            backgroundColor: color,
            height: active ? undefined : `${staticHeights[i]}px`,
            opacity: active ? undefined : 0.35,
          }}
        />
      ))}
    </div>
  )
}
