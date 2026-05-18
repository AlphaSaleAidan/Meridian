import { useState, useEffect } from 'react'

const MOBILE_BREAKPOINT = 768
const TABLET_BREAKPOINT = 1024

function getDevice() {
  if (typeof window === 'undefined') return { isMobile: false, isTablet: false, isDesktop: true }
  const w = window.innerWidth
  return {
    isMobile: w < MOBILE_BREAKPOINT,
    isTablet: w >= MOBILE_BREAKPOINT && w < TABLET_BREAKPOINT,
    isDesktop: w >= TABLET_BREAKPOINT,
  }
}

export function useMobile() {
  const [device, setDevice] = useState(getDevice)

  useEffect(() => {
    function handleResize() { setDevice(getDevice()) }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return device
}

export function useIsMobile(): boolean {
  return useMobile().isMobile
}
