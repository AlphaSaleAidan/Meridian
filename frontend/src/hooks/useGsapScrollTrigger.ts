import { useEffect, useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

interface ScrollTriggerOptions {
  start?: string
  end?: string
  scrub?: boolean | number
  pin?: boolean
  markers?: boolean
  toggleActions?: string
}

export function useGsapTimeline(opts: ScrollTriggerOptions = {}) {
  const triggerRef = useRef<HTMLDivElement>(null)
  const tlRef = useRef<gsap.core.Timeline | null>(null)

  useEffect(() => {
    if (!triggerRef.current) return

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: triggerRef.current,
        start: opts.start ?? 'top 80%',
        end: opts.end ?? 'bottom 20%',
        scrub: opts.scrub ?? false,
        pin: opts.pin ?? false,
        markers: opts.markers ?? false,
      },
    })
    tlRef.current = tl

    return () => {
      tl.scrollTrigger?.kill()
      tl.kill()
    }
  }, [])

  return { triggerRef, timeline: tlRef }
}

export function useGsapFrom(vars: gsap.TweenVars, triggerOpts: ScrollTriggerOptions = {}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return

    const ctx = gsap.context(() => {
      gsap.from(ref.current!, {
        ...vars,
        scrollTrigger: {
          trigger: ref.current!,
          start: triggerOpts.start ?? 'top 85%',
          toggleActions: 'play none none none',
          ...triggerOpts,
        },
      })
    }, ref)

    return () => ctx.revert()
  }, [])

  return ref
}
