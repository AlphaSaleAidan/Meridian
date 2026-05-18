export interface GestureResult {
  gesture: string
  confidence: number
  description: string
}

interface Landmark {
  x: number
  y: number
  z: number
  visibility?: number
}

const GESTURE_DESCRIPTIONS: Record<string, string> = {
  reaching: 'Arms raised above shoulders — examining high shelves or signage',
  browsing: 'Leaning forward with hands extended — inspecting products',
  pointing: 'Arm extended toward object — directing attention',
  carrying: 'Hands below hips with weight — holding items',
  waiting: 'Standing still, arms at sides — idle or in queue',
  walking: 'In motion — traversing the space',
  unknown: 'Pose not classified',
}

export function classifyGesture(landmarks: Landmark[]): GestureResult {
  if (!landmarks || landmarks.length < 25) {
    return { gesture: 'unknown', confidence: 0, description: GESTURE_DESCRIPTIONS.unknown }
  }

  const lShoulder = landmarks[11]
  const rShoulder = landmarks[12]
  const lWrist = landmarks[15]
  const rWrist = landmarks[16]
  const lHip = landmarks[23]
  const rHip = landmarks[24]
  const lAnkle = landmarks[27]
  const rAnkle = landmarks[28]

  if (!lShoulder || !rShoulder || !lWrist || !rWrist || !lHip || !rHip || !lAnkle || !rAnkle) {
    return { gesture: 'unknown', confidence: 0, description: GESTURE_DESCRIPTIONS.unknown }
  }

  const shoulderY = (lShoulder.y + rShoulder.y) / 2
  const hipY = (lHip.y + rHip.y) / 2
  const wristY = Math.min(lWrist.y, rWrist.y)
  const torsoLean = Math.abs(shoulderY - hipY)

  const dx = lAnkle.x - rAnkle.x
  const dy = lAnkle.y - rAnkle.y
  const ankleDistance = Math.sqrt(dx * dx + dy * dy)
  const ankleStill = ankleDistance < 0.15

  // Note: In MediaPipe, y increases downward (0=top, 1=bottom)
  // So "wrist above shoulder" means wristY < shoulderY
  if (wristY < shoulderY - 0.05) {
    return { gesture: 'reaching', confidence: 0.75, description: GESTURE_DESCRIPTIONS.reaching }
  }

  const lWristForward = lWrist.z < lShoulder.z - 0.1
  const rWristForward = rWrist.z < rShoulder.z - 0.1
  if (lWristForward || rWristForward) {
    if (torsoLean > 0.1) {
      return { gesture: 'browsing', confidence: 0.65, description: GESTURE_DESCRIPTIONS.browsing }
    }
    return { gesture: 'pointing', confidence: 0.60, description: GESTURE_DESCRIPTIONS.pointing }
  }

  const wristBelowHip = Math.min(lWrist.y, rWrist.y) > hipY + 0.1
  if (wristBelowHip) {
    return { gesture: 'carrying', confidence: 0.55, description: GESTURE_DESCRIPTIONS.carrying }
  }

  if (ankleStill && torsoLean < 0.05) {
    return { gesture: 'waiting', confidence: 0.70, description: GESTURE_DESCRIPTIONS.waiting }
  }

  return { gesture: 'walking', confidence: 0.50, description: GESTURE_DESCRIPTIONS.walking }
}

export function computeEngagement(landmarks: Landmark[]): number {
  if (!landmarks || landmarks.length < 12) return 0

  const nose = landmarks[0]
  const lShoulder = landmarks[11]
  const rShoulder = landmarks[12]

  if (!nose || !lShoulder || !rShoulder) return 0

  const shoulderMidX = (lShoulder.x + rShoulder.x) / 2
  const facingCamera = 1 - Math.min(Math.abs(nose.x - shoulderMidX) * 4, 1)
  const visibilityScore = (nose.visibility || 0) * 0.5 + (lShoulder.visibility || 0) * 0.25 + (rShoulder.visibility || 0) * 0.25

  return Math.min(facingCamera * visibilityScore * 1.2, 1)
}
