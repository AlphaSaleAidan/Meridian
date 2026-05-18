import { useRef, useState, useCallback, useEffect } from 'react'

interface TrackingState {
  isLoading: boolean
  isReady: boolean
  error: string | null
  fps: number
  poseResults: any | null
  handResults: any | null
  faceResults: any | null
  objectResults: any | null
}

interface TrackingConfig {
  pose: boolean
  hands: boolean
  face: boolean
  objects: boolean
}

const CDN_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.17/wasm'

export function useMediaPipeTracking(videoRef: React.RefObject<HTMLVideoElement | null>, config: TrackingConfig) {
  const [state, setState] = useState<TrackingState>({
    isLoading: false,
    isReady: false,
    error: null,
    fps: 0,
    poseResults: null,
    handResults: null,
    faceResults: null,
    objectResults: null,
  })

  const poseLandmarkerRef = useRef<any>(null)
  const handLandmarkerRef = useRef<any>(null)
  const faceLandmarkerRef = useRef<any>(null)
  const objectDetectorRef = useRef<any>(null)
  const animFrameRef = useRef<number>(0)
  const lastTimeRef = useRef<number>(0)
  const fpsCounterRef = useRef<number[]>([])
  const runningRef = useRef(false)
  const configRef = useRef(config)

  configRef.current = config

  const initialize = useCallback(async () => {
    setState(s => ({ ...s, isLoading: true, error: null }))

    try {
      const vision = await import('@mediapipe/tasks-vision')
      const { FilesetResolver, PoseLandmarker, HandLandmarker, FaceLandmarker, ObjectDetector } = vision

      const filesetResolver = await FilesetResolver.forVisionTasks(CDN_BASE)

      const [poseLandmarker, handLandmarker, faceLandmarker, objectDetector] = await Promise.all([
        PoseLandmarker.createFromOptions(filesetResolver, {
          baseOptions: {
            modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
            delegate: 'GPU',
          },
          runningMode: 'VIDEO',
          numPoses: 3,
        }),
        HandLandmarker.createFromOptions(filesetResolver, {
          baseOptions: {
            modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
            delegate: 'GPU',
          },
          runningMode: 'VIDEO',
          numHands: 4,
        }),
        FaceLandmarker.createFromOptions(filesetResolver, {
          baseOptions: {
            modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
            delegate: 'GPU',
          },
          runningMode: 'VIDEO',
          numFaces: 2,
          outputFaceBlendshapes: true,
        }),
        ObjectDetector.createFromOptions(filesetResolver, {
          baseOptions: {
            modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite',
            delegate: 'GPU',
          },
          runningMode: 'VIDEO',
          maxResults: 10,
          scoreThreshold: 0.4,
        }),
      ])

      poseLandmarkerRef.current = poseLandmarker
      handLandmarkerRef.current = handLandmarker
      faceLandmarkerRef.current = faceLandmarker
      objectDetectorRef.current = objectDetector

      setState(s => ({ ...s, isLoading: false, isReady: true }))
    } catch (err: any) {
      setState(s => ({ ...s, isLoading: false, error: `Failed to load models: ${err.message}` }))
    }
  }, [])

  const startTracking = useCallback(() => {
    if (!state.isReady || runningRef.current) return
    runningRef.current = true

    const detect = () => {
      if (!runningRef.current) return

      const video = videoRef.current
      if (!video || video.readyState < 2) {
        animFrameRef.current = requestAnimationFrame(detect)
        return
      }

      const now = performance.now()
      if (now - lastTimeRef.current < 16) {
        animFrameRef.current = requestAnimationFrame(detect)
        return
      }

      // FPS calculation
      fpsCounterRef.current.push(now)
      fpsCounterRef.current = fpsCounterRef.current.filter(t => now - t < 1000)
      const fps = fpsCounterRef.current.length

      const timestamp = video.currentTime * 1000

      let poseResults = null
      let handResults = null
      let faceResults = null
      let objectResults = null

      try {
        if (configRef.current.pose && poseLandmarkerRef.current) {
          poseResults = poseLandmarkerRef.current.detectForVideo(video, timestamp)
        }
        if (configRef.current.hands && handLandmarkerRef.current) {
          handResults = handLandmarkerRef.current.detectForVideo(video, timestamp)
        }
        if (configRef.current.face && faceLandmarkerRef.current) {
          faceResults = faceLandmarkerRef.current.detectForVideo(video, timestamp)
        }
        if (configRef.current.objects && objectDetectorRef.current) {
          objectResults = objectDetectorRef.current.detectForVideo(video, timestamp)
        }
      } catch {
        // Skip frame on detection error
      }

      lastTimeRef.current = now
      setState(s => ({ ...s, fps, poseResults, handResults, faceResults, objectResults }))

      animFrameRef.current = requestAnimationFrame(detect)
    }

    animFrameRef.current = requestAnimationFrame(detect)
  }, [state.isReady, videoRef])

  const stopTracking = useCallback(() => {
    runningRef.current = false
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current)
    }
  }, [])

  useEffect(() => {
    return () => {
      runningRef.current = false
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      poseLandmarkerRef.current?.close()
      handLandmarkerRef.current?.close()
      faceLandmarkerRef.current?.close()
      objectDetectorRef.current?.close()
    }
  }, [])

  return { ...state, initialize, startTracking, stopTracking }
}
