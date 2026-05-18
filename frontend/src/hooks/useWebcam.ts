import { useRef, useState, useCallback, useEffect } from 'react'

interface WebcamState {
  isActive: boolean
  isLoading: boolean
  error: string | null
  devices: MediaDeviceInfo[]
  activeDeviceId: string
}

export function useWebcam() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [state, setState] = useState<WebcamState>({
    isActive: false,
    isLoading: false,
    error: null,
    devices: [],
    activeDeviceId: '',
  })

  const enumerateDevices = useCallback(async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      const videoDevices = devices.filter(d => d.kind === 'videoinput')
      setState(s => ({ ...s, devices: videoDevices }))
      return videoDevices
    } catch {
      return []
    }
  }, [])

  const start = useCallback(async (deviceId?: string) => {
    setState(s => ({ ...s, isLoading: true, error: null }))

    try {
      const constraints: MediaStreamConstraints = {
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 },
          ...(deviceId ? { deviceId: { exact: deviceId } } : { facingMode: 'user' }),
        },
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      const track = stream.getVideoTracks()[0]
      const activeId = track.getSettings().deviceId || ''

      await enumerateDevices()
      setState(s => ({ ...s, isActive: true, isLoading: false, activeDeviceId: activeId }))
    } catch (err: any) {
      const msg = err.name === 'NotAllowedError'
        ? 'Camera access denied. Please allow camera permissions.'
        : err.name === 'NotFoundError'
        ? 'No camera found on this device.'
        : `Camera error: ${err.message}`
      setState(s => ({ ...s, isLoading: false, error: msg }))
    }
  }, [enumerateDevices])

  const stop = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setState(s => ({ ...s, isActive: false, activeDeviceId: '' }))
  }, [])

  const switchCamera = useCallback(async (deviceId: string) => {
    stop()
    await start(deviceId)
  }, [stop, start])

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
      }
    }
  }, [])

  return { videoRef, ...state, start, stop, switchCamera }
}
