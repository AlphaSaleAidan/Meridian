/**
 * Publish an element's height as a CSS variable while it is on screen.
 *
 * The portal scrolls inside <main>, not the document, and several bars are
 * position:fixed over the bottom of it — the mobile tab bar, the cookie
 * consent banner. Fixed elements are outside flow, so <main> had no idea they
 * were there and gave itself no room for them: you could scroll to the true
 * end of the container and still have the last 150-200 pixels sitting behind
 * a bar. It reads exactly like "it will not scroll to the bottom", because
 * that content is unreachable by any means.
 *
 * Padding <main> by a hard-coded number would be wrong in both directions —
 * the cookie banner is dismissible (leaving a permanent gap for everyone who
 * has consented) and it wraps to two or three lines depending on width. So
 * each bar measures itself and publishes, and the scroll container pads by
 * the sum. A bar that unmounts clears its own variable.
 */
import { useEffect, type RefObject } from 'react'

export function usePublishHeight(
  ref: RefObject<HTMLElement | null>,
  cssVar: string,
  active = true,
): void {
  useEffect(() => {
    const root = document.documentElement
    const el = ref.current
    if (!active || !el) {
      root.style.setProperty(cssVar, '0px')
      return
    }

    const publish = () => {
      root.style.setProperty(cssVar, `${Math.ceil(el.getBoundingClientRect().height)}px`)
    }
    publish()

    // Height changes with viewport width (the banner's text wraps), so a
    // one-shot measurement is wrong the moment somebody rotates a phone.
    const observer = new ResizeObserver(publish)
    observer.observe(el)

    return () => {
      observer.disconnect()
      // Cleared, not left behind: a dismissed banner must not keep reserving
      // space for the rest of the session.
      root.style.setProperty(cssVar, '0px')
    }
  }, [ref, cssVar, active])
}
