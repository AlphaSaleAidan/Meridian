// Live radar favicon: replaces the static meridian-icon.svg with a canvas-
// drawn radar whose sweep spins the whole time a Meridian tab is open.
// The sweep angle derives from the wall clock, so even when the browser
// throttles background-tab timers to ~1 update/second the radar stays on
// time and never drifts — it just steps instead of gliding until the tab
// is foregrounded again. Matches the static icon's palette (meridian-icon.svg).

const SIZE = 32
const PERIOD_MS = 4000 // one full rotation
const TEAL = '#17C5B0'

function rgba(alpha: number): string {
  return `rgba(23, 197, 176, ${alpha})`
}

export function startRadarFavicon(): void {
  if (typeof document === 'undefined') return

  const canvas = document.createElement('canvas')
  canvas.width = SIZE
  canvas.height = SIZE
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]')
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.type = 'image/png'

  const c = SIZE / 2
  // Fixed contact blip on the scope (bearing 40°, range 8px) that lights up
  // as the sweep passes and fades behind it.
  const BLIP_BEARING = (40 * Math.PI) / 180
  const BLIP_X = c + Math.cos(BLIP_BEARING) * 8
  const BLIP_Y = c + Math.sin(BLIP_BEARING) * 8

  const draw = () => {
    const angle = ((Date.now() % PERIOD_MS) / PERIOD_MS) * Math.PI * 2

    ctx.clearRect(0, 0, SIZE, SIZE)
    ctx.save()
    ctx.beginPath()
    ctx.arc(c, c, c - 1, 0, Math.PI * 2)
    ctx.clip()

    // Scope background (same gradient as the static SVG icon)
    const bg = ctx.createRadialGradient(c, c, 0, c, c, c)
    bg.addColorStop(0, '#0D2A4A')
    bg.addColorStop(1, '#0A0A0B')
    ctx.fillStyle = bg
    ctx.fillRect(0, 0, SIZE, SIZE)

    // Range rings + crosshair
    ctx.strokeStyle = rgba(0.28)
    ctx.lineWidth = 1
    for (const r of [13, 8.5, 4]) {
      ctx.beginPath()
      ctx.arc(c, c, r, 0, Math.PI * 2)
      ctx.stroke()
    }
    ctx.strokeStyle = rgba(0.14)
    ctx.beginPath()
    ctx.moveTo(c, 1); ctx.lineTo(c, SIZE - 1)
    ctx.moveTo(1, c); ctx.lineTo(SIZE - 1, c)
    ctx.stroke()

    // Sweep trail — conic gradient peaking at the sweep line, fading behind it
    if (typeof ctx.createConicGradient === 'function') {
      const trail = ctx.createConicGradient(angle, c, c)
      trail.addColorStop(0, rgba(0))
      trail.addColorStop(0.72, rgba(0))
      trail.addColorStop(1, rgba(0.5))
      ctx.fillStyle = trail
      ctx.fillRect(0, 0, SIZE, SIZE)
    } else {
      // Older engines: stepped wedges behind the sweep line
      for (let i = 0; i < 10; i++) {
        ctx.beginPath()
        ctx.moveTo(c, c)
        ctx.arc(c, c, c - 2, angle - ((i + 1) * 0.09), angle - (i * 0.09))
        ctx.closePath()
        ctx.fillStyle = rgba(0.4 * (1 - i / 10))
        ctx.fill()
      }
    }

    // Sweep line
    ctx.strokeStyle = rgba(0.95)
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ctx.moveTo(c, c)
    ctx.lineTo(c + Math.cos(angle) * (c - 2), c + Math.sin(angle) * (c - 2))
    ctx.stroke()

    // Contact blip: brightest as the sweep passes, decays over the next ~120°
    const behind = (angle - BLIP_BEARING + Math.PI * 2) % (Math.PI * 2)
    const blipAlpha = behind < 2.1 ? 1 - behind / 2.1 : 0
    if (blipAlpha > 0.02) {
      ctx.fillStyle = rgba(blipAlpha)
      ctx.beginPath()
      ctx.arc(BLIP_X, BLIP_Y, 1.6, 0, Math.PI * 2)
      ctx.fill()
    }

    // Center hub
    ctx.fillStyle = rgba(0.9)
    ctx.beginPath()
    ctx.arc(c, c, 1.5, 0, Math.PI * 2)
    ctx.fill()

    ctx.restore()

    // Rim
    ctx.strokeStyle = rgba(0.35)
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.arc(c, c, c - 1, 0, Math.PI * 2)
    ctx.stroke()

    link!.href = canvas.toDataURL('image/png')
  }

  draw()
  setInterval(draw, 100)
}
