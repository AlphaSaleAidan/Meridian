import { useState } from 'react'
import QRCode from 'qrcode'
import { Smartphone, Loader2, CheckCircle, Copy } from 'lucide-react'
import { getAuthHeaders } from '@/lib/supabase'

/**
 * Zero-hardware camera connect — Path A entry point.
 *
 * Registers the merchant's phone/tablet as a `source='browser'` camera and shows a
 * QR code that opens the /cam PWA page on that phone. The "Bluetooth-easy" moment:
 * scan the code, allow the camera, prop the phone — no app, no appliance, no Jetson.
 */
export default function PhoneCameraCard({ orgId }: { orgId: string }) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle')
  const [qrDataUrl, setQrDataUrl] = useState('')
  const [camUrl, setCamUrl] = useState('')
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  const apiBase = (import.meta.env.VITE_API_URL || '') as string

  const generate = async () => {
    setStatus('loading')
    setError('')
    try {
      const res = await fetch(`${apiBase}/api/vision/camera/register-browser`, {
        method: 'POST',
        headers: { ...(await getAuthHeaders()) },
        body: JSON.stringify({ org_id: orgId, name: 'Phone camera' }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Could not create a phone camera link')
        setStatus('error')
        return
      }
      const data = await res.json()
      const url = data.cam_url as string
      setCamUrl(url)
      setQrDataUrl(await QRCode.toDataURL(url, { width: 240, margin: 1 }))
      setStatus('ready')
    } catch {
      setError('Could not reach the server. Please try again.')
      setStatus('error')
    }
  }

  const copyLink = () => {
    navigator.clipboard?.writeText(camUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className="p-4 rounded-xl border border-[#17C5B0]/30 bg-[#17C5B0]/5">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-[#17C5B0]/15 flex items-center justify-center flex-shrink-0">
          <Smartphone size={18} className="text-[#17C5B0]" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Use a phone — no hardware</h3>
            <span className="text-[8px] font-bold text-[#17C5B0] bg-[#17C5B0]/10 px-1.5 py-0.5 rounded">
              FASTEST
            </span>
          </div>
          <p className="text-[11px] text-[#A1A1A8] mt-1">
            Turn any spare phone or tablet you already own into a camera. Scan the code,
            allow the camera, prop it at the space. Nothing to buy, nothing to install.
          </p>

          {status === 'idle' && (
            <button
              onClick={generate}
              className="mt-3 px-3 py-1.5 text-[11px] font-medium rounded-lg bg-[#17C5B0] text-white hover:bg-[#17C5B0]/90 transition-colors"
            >
              Get a phone camera link
            </button>
          )}

          {status === 'loading' && (
            <div className="mt-3 flex items-center gap-2 text-[11px] text-[#A1A1A8]">
              <Loader2 size={14} className="animate-spin" /> Creating link…
            </div>
          )}

          {status === 'error' && (
            <div className="mt-3 space-y-2">
              <p className="text-[11px] text-red-400">{error}</p>
              <button
                onClick={generate}
                className="px-3 py-1.5 text-[11px] rounded-lg bg-[#1F1F23] text-[#F5F5F7] hover:bg-[#2A2A2E]"
              >
                Try again
              </button>
            </div>
          )}

          {status === 'ready' && (
            <div className="mt-3 flex flex-col sm:flex-row items-start gap-4">
              <div className="p-2 rounded-lg bg-white">
                {qrDataUrl && <img src={qrDataUrl} alt="Scan to open camera on your phone" width={140} height={140} />}
              </div>
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-1.5 text-[11px] text-[#17C5B0]">
                  <CheckCircle size={13} /> Scan with your phone's camera app
                </div>
                <p className="text-[10px] text-[#A1A1A8]/70">
                  Or copy the link and open it on the device you want to use as a camera.
                </p>
                <button
                  onClick={copyLink}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] rounded-md bg-[#1F1F23] text-[#F5F5F7] hover:bg-[#2A2A2E]"
                >
                  <Copy size={11} /> {copied ? 'Copied!' : 'Copy link'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
