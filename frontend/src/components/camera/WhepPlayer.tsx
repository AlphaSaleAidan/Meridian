import { useEffect, useRef } from 'react'

/**
 * WHEP WebRTC player (sub-second) with native-HLS fallback.
 * WHEP = POST our SDP offer to whepUrl, set the SDP answer. No library needed.
 * Fallback: Safari/iOS play HLS natively via <video src=m3u8>; other browsers can
 * lazy-load hls.js later. ponytail: native first, no dep.
 */
export default function WhepPlayer({
  whepUrl, hlsUrl, token, onVideoRef,
}: {
  whepUrl: string
  hlsUrl?: string
  token: string
  onVideoRef?: (el: HTMLVideoElement | null) => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    onVideoRef?.(video)
    let pc: RTCPeerConnection | null = null
    let cancelled = false

    async function startWhep() {
      pc = new RTCPeerConnection()
      pc.addTransceiver('video', { direction: 'recvonly' })
      pc.addTransceiver('audio', { direction: 'recvonly' })
      pc.ontrack = (e) => { if (video) video.srcObject = e.streams[0] }
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      const res = await fetch(whepUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp', Authorization: `Bearer ${token}` },
        body: offer.sdp,
      })
      if (!res.ok) throw new Error(`WHEP ${res.status}`)
      const answer = await res.text()
      if (cancelled) return
      await pc.setRemoteDescription({ type: 'answer', sdp: answer })
    }

    function startHls() {
      if (!video || !hlsUrl) return
      // Safari / iOS play HLS natively. (Chrome/FF: add hls.js as an enhancement.)
      if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = `${hlsUrl}?jwt=${encodeURIComponent(token)}`
        video.play().catch(() => {})
      }
    }

    startWhep().catch(() => { if (!cancelled) startHls() })

    return () => {
      cancelled = true
      pc?.close()
      if (video) { video.srcObject = null; video.removeAttribute('src') }
      onVideoRef?.(null)
    }
  }, [whepUrl, hlsUrl, token, onVideoRef])

  return (
    <video
      ref={videoRef}
      autoPlay muted playsInline
      className="w-full h-full object-cover bg-black"
    />
  )
}
