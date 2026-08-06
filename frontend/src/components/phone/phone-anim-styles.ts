/** Inject animation keyframes for phone-orders UI (idempotent). */
const ANIM_STYLE_ID = 'phone-orders-anims'

export function ensureAnimStyles() {
  if (typeof document === 'undefined') return
  if (document.getElementById(ANIM_STYLE_ID)) return
  const style = document.createElement('style')
  style.id = ANIM_STYLE_ID
  style.textContent = `
    @keyframes waveBar {
      0%, 100% { height: 4px; }
      50% { height: 16px; }
    }
    .wave-bar { animation: waveBar 1.2s ease-in-out infinite; }
    .wave-bar:nth-child(2) { animation-delay: 0.15s; }
    .wave-bar:nth-child(3) { animation-delay: 0.3s; }
    .wave-bar:nth-child(4) { animation-delay: 0.45s; }
    .wave-bar:nth-child(5) { animation-delay: 0.6s; }
    .wave-bar:nth-child(6) { animation-delay: 0.75s; }
    .wave-bar:nth-child(7) { animation-delay: 0.9s; }
    .wave-bar:nth-child(8) { animation-delay: 1.05s; }
    .wave-bar:nth-child(9) { animation-delay: 0.2s; }
    .wave-bar:nth-child(10) { animation-delay: 0.35s; }
    .wave-bar:nth-child(11) { animation-delay: 0.5s; }
    .wave-bar:nth-child(12) { animation-delay: 0.65s; }
    .wave-bar:nth-child(13) { animation-delay: 0.8s; }
    .wave-bar:nth-child(14) { animation-delay: 0.95s; }
    .wave-bar:nth-child(15) { animation-delay: 0.1s; }
    .wave-bar:nth-child(16) { animation-delay: 0.25s; }
    @keyframes livePulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(23,197,176,0.4); }
      50% { box-shadow: 0 0 0 6px rgba(23,197,176,0); }
    }
    .live-pulse-ring { animation: livePulse 2s ease-in-out infinite; }
    @keyframes testCallRing {
      0%, 100% { transform: rotate(0deg); }
      10% { transform: rotate(15deg); }
      20% { transform: rotate(-15deg); }
      30% { transform: rotate(10deg); }
      40% { transform: rotate(-10deg); }
      50% { transform: rotate(0deg); }
    }
    .test-call-ring { animation: testCallRing 1.5s ease-in-out infinite; }
    @keyframes waveformPulse {
      0%, 100% { opacity: 0.4; }
      50% { opacity: 1; }
    }
    .waveform-pulse { animation: waveformPulse 1.5s ease-in-out infinite; }
    @keyframes embedReveal {
      from { opacity: 0; transform: translateY(-4px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .embed-reveal { animation: embedReveal 260ms cubic-bezier(0.22, 1, 0.36, 1); }
    @media (prefers-reduced-motion: reduce) {
      .embed-reveal { animation: none; }
    }
  `
  document.head.appendChild(style)
}
