import { useState } from 'react'
import {
  Camera, CheckCircle, Shield, X, ChevronLeft, ChevronRight,
  QrCode, Cloud, Terminal, Copy, Loader2, Info,
} from 'lucide-react'
import { clsx } from 'clsx'
import { getAuthHeaders } from '@/lib/supabase'

// Corrected direction (Aidan): connect the merchant's ALREADY-INSTALLED cameras with ZERO
// shipped hardware. Options are ordered by friction, easiest first:
//   PRIMARY  — vendor-cloud: scan the QR sticker on the camera, or pick the brand and log
//              into the camera app they already use (OAuth). Cloud-to-cloud, no install.
//   FALLBACK — one-line LAN connector: a single `docker run` on a PC they already own; it
//              auto-discovers ONVIF cameras. No hardware, no RTSP typing, no port-forward.
//   ADVANCED — manual RTSP (legacy, for power users).
// Anonymous analytics only; the biometric identity tier stays gated server-side.

type Method = 'vendor' | 'connector' | 'manual'

interface CameraSetupWizardProps {
  orgId: string
  onComplete: (result?: unknown) => void
  onClose: () => void
}

const apiBase = (import.meta.env.VITE_API_URL || '') as string

export default function CameraSetupWizard({ orgId, onComplete, onClose }: CameraSetupWizardProps) {
  const [method, setMethod] = useState<Method | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // LAN connector
  const [pairing, setPairing] = useState<{ pairing_code: string; install_command: string; qr_payload: string } | null>(null)

  // manual RTSP (advanced)
  const [name, setName] = useState('')
  const [rtsp, setRtsp] = useState('')

  const startVendorOAuth = async () => {
    setBusy(true); setError('')
    try {
      const res = await fetch(`${apiBase}/api/vision/connect/vendor/tuya/oauth-url?org_id=${encodeURIComponent(orgId)}`, {
        headers: { ...(await getAuthHeaders()) },
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data.authorize_url) {
        setError(data.detail || 'Camera-cloud connect isn’t available on this deployment yet. Use the one-line connector below.')
        return
      }
      // Send the merchant to their camera vendor's consent screen; they log into the app
      // they already use. On return, the backend links + registers their cameras.
      window.location.href = data.authorize_url as string
    } catch {
      setError('Could not reach the server. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const mintPairingCode = async () => {
    setBusy(true); setError('')
    try {
      const res = await fetch(`${apiBase}/api/vision/connect/pairing-code`, {
        method: 'POST',
        headers: { ...(await getAuthHeaders()) },
        body: JSON.stringify({ org_id: orgId }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setError(data.detail || 'Could not create a pairing code.')
        return
      }
      setPairing(data)
    } catch {
      setError('Could not reach the server. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const submitManual = async () => {
    setError('')
    if (!/^rtsp:\/\/.+/i.test(rtsp)) {
      setError('Enter a valid RTSP URL (e.g., rtsp://192.168.1.100:554/stream1)')
      return
    }
    try {
      const res = await fetch(`${apiBase}/api/vision/cameras`, {
        method: 'POST',
        headers: { ...(await getAuthHeaders()) },
        body: JSON.stringify({ org_id: orgId, name, rtsp_url: rtsp, compliance_mode: 'anonymous' }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Failed to register camera')
        return
      }
      onComplete()
    } catch {
      setError('Could not reach the server. Please try again.')
    }
  }

  const copy = (text: string) => { try { void navigator.clipboard?.writeText(text) } catch { /* noop */ } }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[#111113] border border-[#1F1F23] rounded-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23]">
          <div className="flex items-center gap-2">
            <Camera size={16} className="text-[#1A8FD6]" />
            <h2 className="text-sm font-semibold text-[#F5F5F7]">Connect your cameras</h2>
          </div>
          <button aria-label="Close setup" onClick={onClose} className="text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="px-5 py-5 space-y-4">
          {/* Method picker (default) */}
          {!method && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Use the cameras you already have</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  No new hardware. Connect your existing security cameras &mdash; pick the easiest option.
                </p>
              </div>

              {/* PRIMARY — vendor-cloud */}
              <button
                onClick={() => setMethod('vendor')}
                className="w-full p-3 rounded-lg border border-[#1A8FD6]/40 bg-[#1A8FD6]/5 text-left hover:bg-[#1A8FD6]/10 transition-all"
              >
                <div className="flex items-center gap-2">
                  <Cloud size={15} className="text-[#1A8FD6]" />
                  <span className="text-xs font-medium text-[#F5F5F7]">Connect via your camera app</span>
                  <span className="ml-auto text-[8px] font-bold text-[#17C5B0] bg-[#17C5B0]/10 px-1.5 py-0.5 rounded">EASIEST</span>
                </div>
                <p className="text-[10px] text-[#A1A1A8]/70 mt-1 ml-6">
                  Scan the sticker on your camera or log into the app you already use (Smart Life &amp; more).
                  Nothing to install.
                </p>
              </button>

              {/* FALLBACK — LAN connector */}
              <button
                onClick={() => setMethod('connector')}
                className="w-full p-3 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-left hover:border-[#A1A1A8]/20 transition-all"
              >
                <div className="flex items-center gap-2">
                  <Terminal size={15} className="text-[#A1A1A8]" />
                  <span className="text-xs font-medium text-[#F5F5F7]">One-line connector</span>
                </div>
                <p className="text-[10px] text-[#A1A1A8]/60 mt-1 ml-6">
                  Camera brand not supported above? Run one command on a PC you already have on the same
                  network. It finds your cameras automatically &mdash; no hardware, no RTSP URLs.
                </p>
              </button>

              {/* ADVANCED — manual RTSP */}
              <button
                onClick={() => setMethod('manual')}
                className="w-full text-left text-[10px] text-[#A1A1A8]/50 hover:text-[#A1A1A8] transition-colors"
              >
                Advanced: enter an RTSP URL manually &rarr;
              </button>
            </>
          )}

          {/* VENDOR-CLOUD */}
          {method === 'vendor' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Connect via your camera app</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  We connect to the cameras you already have, through the camera cloud &mdash; nothing to install.
                </p>
              </div>
              <div className="p-3 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] flex items-start gap-2">
                <QrCode size={16} className="text-[#1A8FD6] flex-shrink-0 mt-0.5" />
                <div className="text-[10px] text-[#A1A1A8]">
                  <p className="text-[#F5F5F7] font-medium text-[11px]">Scan the sticker on your camera</p>
                  <p className="mt-0.5">Most cameras have a QR/serial sticker. Scan it, then authorize your camera
                    account once. (Sticker scanning links to the same authorize step.)</p>
                </div>
              </div>
              <button
                onClick={startVendorOAuth}
                disabled={busy}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-[11px] font-semibold rounded-lg bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 transition-colors disabled:opacity-50"
              >
                {busy ? <Loader2 size={13} className="animate-spin" /> : <Cloud size={13} />}
                Authorize my camera account
              </button>
              {error && <p className="text-[10px] text-amber-400">{error}</p>}
            </>
          )}

          {/* LAN CONNECTOR */}
          {method === 'connector' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">One-line connector</h3>
                <p className="text-[11px] text-[#A1A1A8]">
                  Run this on any PC/POS terminal on the same network as your cameras. It dials out to
                  Meridian and auto-discovers your cameras &mdash; no hardware, no router changes.
                </p>
              </div>
              {!pairing ? (
                <button
                  onClick={mintPairingCode}
                  disabled={busy}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-[11px] font-semibold rounded-lg bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 transition-colors disabled:opacity-50"
                >
                  {busy ? <Loader2 size={13} className="animate-spin" /> : <Terminal size={13} />}
                  Get my connect command
                </button>
              ) : (
                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Run this one line</label>
                    <div className="flex items-start gap-2 p-2.5 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]">
                      <code className="text-[10px] text-[#17C5B0] font-mono break-all flex-1">{pairing.install_command}</code>
                      <button aria-label="Copy command" onClick={() => copy(pairing.install_command)} className="text-[#A1A1A8] hover:text-[#F5F5F7] flex-shrink-0">
                        <Copy size={13} />
                      </button>
                    </div>
                  </div>
                  <div className="flex items-start gap-2 p-2.5 rounded-lg border border-[#1F1F23]/50 bg-[#17C5B0]/5">
                    <Info size={13} className="text-[#17C5B0] flex-shrink-0 mt-0.5" />
                    <p className="text-[10px] text-[#A1A1A8]">
                      Your cameras appear here within seconds of running it. Camera passwords stay on that
                      machine and never reach the cloud. Code expires in 15 minutes.
                    </p>
                  </div>
                  <button
                    onClick={() => onComplete()}
                    className="w-full flex items-center justify-center gap-1.5 px-4 py-2 text-[11px] font-semibold rounded-lg bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 transition-colors"
                  >
                    <CheckCircle size={12} /> Done &mdash; I ran the command
                  </button>
                </div>
              )}
              {error && <p className="text-[10px] text-amber-400">{error}</p>}
            </>
          )}

          {/* MANUAL RTSP (advanced) */}
          {method === 'manual' && (
            <>
              <div>
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">Advanced: RTSP URL</h3>
                <p className="text-[11px] text-[#A1A1A8]">For power users who already know their camera&rsquo;s RTSP URL.</p>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">Camera Name</label>
                  <input
                    type="text" value={name} onChange={e => setName(e.target.value)}
                    placeholder="e.g., Front Door, Checkout Area"
                    className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-medium text-[#A1A1A8] mb-1 block">RTSP URL</label>
                  <input
                    type="text" value={rtsp} onChange={e => setRtsp(e.target.value)}
                    placeholder="rtsp://192.168.1.100:554/stream1"
                    className="w-full px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40 font-mono"
                  />
                </div>
                <button
                  onClick={submitManual}
                  disabled={!name || !rtsp}
                  className={clsx(
                    'w-full flex items-center justify-center gap-1.5 px-4 py-2 text-[11px] font-semibold rounded-lg transition-colors',
                    name && rtsp ? 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90' : 'bg-[#1F1F23] text-[#A1A1A8]/40 cursor-not-allowed',
                  )}
                >
                  <CheckCircle size={12} /> Add camera
                </button>
              </div>
              {error && <p className="text-[10px] text-amber-400">{error}</p>}
            </>
          )}

          {/* Privacy note — always visible */}
          <div className="flex items-start gap-2 p-3 rounded-lg border border-[#1F1F23]/50 bg-[#17C5B0]/5">
            <Shield size={14} className="text-[#17C5B0] flex-shrink-0 mt-0.5" />
            <p className="text-[10px] text-[#A1A1A8]">
              Anonymous analytics only &mdash; aggregate counts, no face data. No raw video is stored in the cloud.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-4 border-t border-[#1F1F23]">
          <button
            onClick={() => { if (method) { setMethod(null); setPairing(null); setError('') } else { onClose() } }}
            className="flex items-center gap-1 text-[11px] text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
          >
            <ChevronLeft size={12} />
            {method ? 'Back' : 'Cancel'}
          </button>
          {!method && (
            <span className="flex items-center gap-1 text-[10px] text-[#A1A1A8]/40">
              Pick an option above <ChevronRight size={11} />
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
