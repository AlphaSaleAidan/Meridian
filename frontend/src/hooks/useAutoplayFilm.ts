import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Scroll-triggered playback for the brand film, shared by the US and Canada
 * landing pages so the two can't drift apart.
 *
 * Sound is the awkward part. Browsers reject an unmuted play() until the
 * visitor has interacted with the page, and a rejected play means nothing
 * starts at all — so we can never simply ask for sound. Instead:
 *
 *   1. If a gesture already happened before the film scrolls up, start unmuted.
 *   2. If not, start muted and unmute the moment a gesture arrives while the
 *      film is still on screen.
 *   3. If neither, it plays muted with an Unmute control.
 *
 * Scrolling is deliberately not a gesture — no browser accepts it as one, so
 * treating it as such would just produce the rejection we are avoiding.
 */
export function useAutoplayFilm() {
  const ref = useRef<HTMLVideoElement>(null)
  const [muted, setMuted] = useState(true)
  const gestured = useRef(false)
  const visible = useRef(false)
  // Once sound has been turned on automatically we stop doing it, so that a
  // visitor who deliberately mutes via the native controls is never overridden.
  const autoUnmuted = useRef(false)

  const unmute = useCallback(() => {
    const el = ref.current
    if (!el) return
    autoUnmuted.current = true
    el.muted = false
    setMuted(false)
    el.play().catch(() => {})
  }, [])

  useEffect(() => {
    const onGesture = () => {
      gestured.current = true
      if (visible.current && !autoUnmuted.current && ref.current?.muted) unmute()
    }
    window.addEventListener('pointerdown', onGesture)
    window.addEventListener('keydown', onGesture)
    return () => {
      window.removeEventListener('pointerdown', onGesture)
      window.removeEventListener('keydown', onGesture)
    }
  }, [unmute])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    // Someone who asked the OS for less motion did not ask for a video to start
    // itself; leave them the poster and the normal play control.
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return

    const io = new IntersectionObserver(
      async ([entry]) => {
        visible.current = entry.isIntersecting
        if (!entry.isIntersecting) {
          if (!el.paused) el.pause()
          return
        }
        if (gestured.current && !autoUnmuted.current) {
          el.muted = false
          try {
            await el.play()
            autoUnmuted.current = true
            setMuted(false)
            return
          } catch {
            // Browser refused sound after all — fall through to muted.
          }
        }
        if (!autoUnmuted.current) {
          el.muted = true
          setMuted(true)
        }
        el.play().catch(() => {})
      },
      { threshold: 0.5 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return { ref, muted, unmute }
}
