type ScanTier = 'lidar' | 'standard'

interface DeviceCapabilities {
  tier: ScanTier
  deviceModel: string | null
  hasLiDAR: boolean
  webXRSupported: boolean
  rearCameraSupported: boolean
  maxResolution: 'high' | 'medium'
}

const LIDAR_MODELS = [
  'iPhone 12 Pro', 'iPhone 12 Pro Max',
  'iPhone 13 Pro', 'iPhone 13 Pro Max',
  'iPhone 14 Pro', 'iPhone 14 Pro Max',
  'iPhone 15 Pro', 'iPhone 15 Pro Max',
  'iPhone 16 Pro', 'iPhone 16 Pro Max',
  'iPhone 17 Pro', 'iPhone 17 Pro Max',
  'iPad Pro 11', 'iPad Pro 12.9',
]

function detectiPhoneModel(): string | null {
  const ua = navigator.userAgent
  if (!/iPhone|iPad/.test(ua)) return null

  const screenW = window.screen.width
  const screenH = window.screen.height
  const dpr = window.devicePixelRatio
  const maxDim = Math.max(screenW, screenH)
  const minDim = Math.min(screenW, screenH)

  if (/iPad/.test(ua)) {
    if (dpr >= 2 && maxDim >= 1024) return 'iPad Pro 11'
    return 'iPad'
  }

  // iPhone model heuristics based on logical screen dimensions + DPR
  if (dpr === 3) {
    if (maxDim === 932 && minDim === 430) return 'iPhone 15 Pro Max'
    if (maxDim === 852 && minDim === 393) return 'iPhone 15 Pro'
    if (maxDim === 926 && minDim === 428) return 'iPhone 14 Pro Max'
    if (maxDim === 844 && minDim === 390) return 'iPhone 14 Pro'
    if (maxDim === 896 && minDim === 414) return 'iPhone 13 Pro Max'
    if (maxDim === 844 && minDim === 390) return 'iPhone 13 Pro'
    if (maxDim === 926 && minDim === 428) return 'iPhone 12 Pro Max'
    if (maxDim === 844 && minDim === 390) return 'iPhone 12 Pro'
    if (maxDim === 812 && minDim === 375) return 'iPhone X'
    if (maxDim === 736 && minDim === 414) return 'iPhone 8 Plus'
    if (maxDim === 667 && minDim === 375) return 'iPhone 8'
  }
  if (dpr === 2) {
    if (maxDim === 667 && minDim === 375) return 'iPhone SE'
    if (maxDim === 568 && minDim === 320) return 'iPhone SE (1st)'
  }

  return 'iPhone (unknown)'
}

function isLiDARDevice(model: string | null): boolean {
  if (!model) return false
  return LIDAR_MODELS.some(m => model.startsWith(m))
}

async function checkWebXR(): Promise<boolean> {
  if (!('xr' in navigator)) return false
  try {
    return await (navigator as any).xr.isSessionSupported('immersive-ar')
  } catch {
    return false
  }
}

export async function getDeviceCapabilities(): Promise<DeviceCapabilities> {
  const deviceModel = detectiPhoneModel()
  const hasLiDAR = isLiDARDevice(deviceModel)
  const webXRSupported = await checkWebXR()
  const isSecure = window.isSecureContext
  const rearCameraSupported = isSecure && 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices

  return {
    tier: hasLiDAR ? 'lidar' : 'standard',
    deviceModel,
    hasLiDAR,
    webXRSupported,
    rearCameraSupported,
    maxResolution: hasLiDAR ? 'high' : 'medium',
  }
}

export function isMobile(): boolean {
  return /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
}

export type { DeviceCapabilities, ScanTier }
