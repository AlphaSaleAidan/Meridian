/**Responsive breakpoint hooks for mobile-first layout.**/
import { useState, useEffect } from 'react'

export const BREAKPOINTS = {
  mobile: 768,
  tablet: 1024,
  desktop: 1280,
} as const

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    const mql = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [query])

  return matches
}

export function useIsMobile(): boolean {
  return !useMediaQuery(`(min-width: ${BREAKPOINTS.mobile}px)`)
}

export function useIsTablet(): boolean {
  const aboveMobile = useMediaQuery(`(min-width: ${BREAKPOINTS.mobile}px)`)
  const belowDesktop = !useMediaQuery(`(min-width: ${BREAKPOINTS.desktop}px)`)
  return aboveMobile && belowDesktop
}

export function useIsDesktop(): boolean {
  return useMediaQuery(`(min-width: ${BREAKPOINTS.desktop}px)`)
}

export function useBreakpoint(): 'mobile' | 'tablet' | 'desktop' {
  const isDesktop = useMediaQuery(`(min-width: ${BREAKPOINTS.desktop}px)`)
  const isTablet = useMediaQuery(`(min-width: ${BREAKPOINTS.mobile}px)`)
  if (isDesktop) return 'desktop'
  if (isTablet) return 'tablet'
  return 'mobile'
}
