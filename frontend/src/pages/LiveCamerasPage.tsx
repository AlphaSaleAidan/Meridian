import { useIsDemo } from '@/hooks/useOrg'
import CameraDemo from '@/components/camera/CameraDemo'

/**
 * Camera → Live tab. On the Canada demo this shows the working camera-
 * intelligence demo (real YOLO+ByteTrack output replayed over a clip). For a
 * real merchant the live WHEP grid isn't wired on main yet, so we show a short
 * "connect a camera" placeholder until that backend lands.
 *
 * ponytail: deliberately demo-only — the live grid + its streaming components
 * arrive with the camera-streaming backend; no point shipping that UI here when
 * nothing serves it. Replace the placeholder branch when that merges.
 */
export default function LiveCamerasPage() {
  if (useIsDemo()) return <CameraDemo />
  return (
    <div className="rounded-2xl border border-dashed border-[#1F1F23] py-12 text-center">
      <p className="text-[13px] text-[#A1A1A8]">Live camera streaming is coming soon.</p>
      <p className="text-[12px] text-[#A1A1A8]/60 mt-1">Your camera-intelligence analytics are in the Analytics tab.</p>
    </div>
  )
}
