import { useCallback, useEffect, useRef, useState } from 'react'

interface FilmApi {
  start(): void
  stop(): void
  mute(): void
  unmute(): void
  isMuted(): boolean
  audioLive(): boolean
}

/**
 * Scroll-triggered playback for the plain-English explainer, following exactly the
 * rules in useAutoplayFilm — the two films on the homepage should behave identically.
 *
 * The difference is what is being driven. The Captains cut is a <video>; this one is a
 * self-contained HTML film in a same-origin iframe, so playback goes through the small
 * control surface it exposes on its own window rather than through media element
 * properties. Reaching in that way keeps the film's transport UI in agreement with what
 * is actually playing, which poking at its <audio> directly would not.
 *
 * The frame is also mounted lazily: 1.5MB should not land on every homepage visit, only
 * on the visits that scroll far enough to watch it.
 */
export function useAutoplayFrameFilm() {
  const holderRef = useRef<HTMLDivElement>(null)
  const frameRef = useRef<HTMLIFrameElement>(null)
  const [mounted, setMounted] = useState(false)
  const [muted, setMuted] = useState(true)
  const gestured = useRef(false)
  const visible = useRef(false)
  const autoUnmuted = useRef(false)

  const api = useCallback((): FilmApi | undefined => {
    try {
      return (frameRef.current?.contentWindow as unknown as { meridianFilm?: FilmApi })?.meridianFilm
    } catch {
      return undefined // frame not ready, or torn down mid-call
    }
  }, [])

  /** Turn sound on, then confirm the browser actually allowed it. */
  const unmute = useCallback(() => {
    const film = api()
    if (!film) return
    autoUnmuted.current = true
    film.unmute()
    setMuted(false)
    window.setTimeout(() => {
      if (!api()?.audioLive()) {
        autoUnmuted.current = false
        setMuted(true)
      }
    }, 300)
  }, [api])

  useEffect(() => {
    const onGesture = () => {
      gestured.current = true
      if (visible.current && !autoUnmuted.current && api()?.isMuted()) unmute()
    }
    window.addEventListener('pointerdown', onGesture)
    window.addEventListener('keydown', onGesture)
    return () => {
      window.removeEventListener('pointerdown', onGesture)
      window.removeEventListener('keydown', onGesture)
    }
  }, [unmute, api])

  // Someone who asked the OS for less motion did not ask for a film to start itself;
  // they keep the poster and a play control. Mirrors useAutoplayFilm.
  const reduced =
    typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

  // Bring the frame in slightly before it is reached, so it is ready to play rather
  // than loading 1.5MB at the moment it becomes visible.
  useEffect(() => {
    const el = holderRef.current
    if (!el || mounted || reduced) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setMounted(true)
          io.disconnect()
        }
      },
      { rootMargin: '400px 0px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [mounted, reduced])

  useEffect(() => {
    const el = holderRef.current
    if (!el || !mounted || reduced) return

    const io = new IntersectionObserver(
      ([entry]) => {
        visible.current = entry.isIntersecting
        const film = api()
        if (!film) return
        if (!entry.isIntersecting) {
          film.stop()
          return
        }
        if (gestured.current && !autoUnmuted.current) {
          unmute()
          return
        }
        if (!autoUnmuted.current) {
          film.mute()
          setMuted(true)
        }
        film.start()
      },
      { threshold: 0.5 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [mounted, reduced, unmute, api])

  // The film keeps its own sound button in the transport, so sound can be changed
  // without going through the Unmute control above. Follow it, or the control ends up
  // claiming the opposite of what the viewer can hear.
  useEffect(() => {
    if (!mounted) return
    const id = window.setInterval(() => {
      const film = api()
      if (!film) return
      const isMuted = film.isMuted()
      setMuted((was) => (was === isMuted ? was : isMuted))
      if (!isMuted) autoUnmuted.current = true
    }, 400)
    return () => window.clearInterval(id)
  }, [mounted, api])

  /** The frame preloads muted and off-screen; hold it until it is actually watched. */
  const onFrameLoad = useCallback(() => {
    // Reduced motion: both observers above are off, so this is the only place the
    // film can start. The frame only mounts there through the explicit play tap, so
    // start it — and try for sound, since a real gesture asked for a narrated film.
    // If the gesture has expired by the time 1.5MB has arrived, unmute() notices the
    // browser refused and falls back to the muted state with the Unmute pill up.
    if (reduced) {
      if (gestured.current) {
        api()?.start()
        unmute()
      }
      return
    }
    if (!visible.current) api()?.stop()
  }, [api, reduced, unmute])

  /** Reduced-motion path: nothing starts until it is asked for. */
  const startManually = useCallback(() => {
    setMounted(true)
    gestured.current = true
  }, [])

  return { holderRef, frameRef, mounted, muted, unmute, onFrameLoad, startManually, reduced }
}
