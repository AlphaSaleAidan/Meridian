import { useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Share, Phone, Mail, Globe, ChevronUp } from 'lucide-react'
import QRCode from 'qrcode'
import { supabase } from '@/lib/supabase'

interface RepInfo {
  name: string
  title: string
  badge_number: string
  email: string
  phone: string
  photo_url?: string
}

function getInitials(name: string): string {
  return name.split(' ').map(w => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase()
}

function generateVCard(rep: RepInfo): string {
  const nameParts = rep.name.split(' ')
  const last = nameParts.length > 1 ? nameParts.pop()! : ''
  const first = nameParts.join(' ')
  return [
    'BEGIN:VCARD',
    'VERSION:3.0',
    `N:${last};${first};;;`,
    `FN:${rep.name}`,
    `TITLE:${rep.title}`,
    `ORG:Meridian`,
    rep.phone ? `TEL;TYPE=WORK:${rep.phone}` : '',
    rep.email ? `EMAIL;TYPE=WORK:${rep.email}` : '',
    `URL:https://meridian.tips`,
    `NOTE:Badge ${rep.badge_number}`,
    'END:VCARD',
  ].filter(Boolean).join('\r\n')
}

export default function WalletCardPage() {
  const { badgeId } = useParams<{ badgeId: string }>()
  const [rep, setRep] = useState<RepInfo | null>(null)
  const [qrUrl, setQrUrl] = useState('')
  const [loading, setLoading] = useState(true)
  const [showTip, setShowTip] = useState(false)
  const [flipped, setFlipped] = useState(false)

  useEffect(() => {
    async function load() {
      if (!badgeId) { setLoading(false); return }

      // Try localStorage first (rep viewing their own card)
      try {
        const stored = localStorage.getItem('meridian_badge_data')
        if (stored) {
          const data = JSON.parse(stored)
          if (data.badge_number === badgeId) {
            setRep(data)
            setLoading(false)
            return
          }
        }
      } catch { /* ignore */ }

      // Try Supabase
      if (supabase) {
        try {
          const { data } = await supabase
            .from('sales_reps')
            .select('name, email, phone')
            .or(`badge_number.eq.${badgeId}`)
            .single()
          if (data) {
            setRep({
              name: data.name,
              title: 'Sales Representative',
              badge_number: badgeId,
              email: data.email || '',
              phone: data.phone || '',
            })
            setLoading(false)
            return
          }
        } catch { /* fallback */ }
      }

      setRep({
        name: 'Meridian Representative',
        title: 'Sales Representative',
        badge_number: badgeId,
        email: '',
        phone: '',
      })
      setLoading(false)
    }
    load()
  }, [badgeId])

  useEffect(() => {
    if (!badgeId) return
    const url = `${window.location.origin}/rep/${encodeURIComponent(badgeId)}`
    QRCode.toDataURL(url, {
      width: 200,
      margin: 1,
      color: { dark: '#ffffff', light: '#00000000' },
      errorCorrectionLevel: 'M',
    }).then(setQrUrl).catch(() => {})
  }, [badgeId])

  function downloadVCard() {
    if (!rep) return
    const vcf = generateVCard(rep)
    const blob = new Blob([vcf], { type: 'text/vcard;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${rep.name.replace(/\s+/g, '-')}.vcf`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function handleShare() {
    if (!rep) return
    const url = `${window.location.origin}/rep/${encodeURIComponent(rep.badge_number)}`
    if (navigator.share) {
      try {
        await navigator.share({
          title: `${rep.name} — Meridian`,
          text: `${rep.name}, ${rep.title} at Meridian`,
          url,
        })
      } catch { /* cancelled */ }
    } else {
      await navigator.clipboard.writeText(url)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#17C5B0] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!rep) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center text-white">
        Badge not found
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center p-4 select-none">
      {/* Card container with flip */}
      <div
        className="w-full max-w-[380px] aspect-[1.6/1] cursor-pointer"
        style={{ perspective: '1200px' }}
        onClick={() => setFlipped(!flipped)}
      >
        <div
          className="relative w-full h-full transition-transform duration-500"
          style={{
            transformStyle: 'preserve-3d',
            transform: flipped ? 'rotateY(180deg)' : 'rotateY(0)',
          }}
        >
          {/* ── FRONT ── */}
          <div
            className="absolute inset-0 rounded-2xl overflow-hidden shadow-2xl"
            style={{
              backfaceVisibility: 'hidden',
              background: 'linear-gradient(135deg, #0d1117 0%, #0a1a2e 40%, #0d2b3e 100%)',
            }}
          >
            <div
              className="absolute inset-0 opacity-[0.03]"
              style={{
                backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
                backgroundSize: '20px 20px',
              }}
            />
            <div className="absolute top-0 left-0 right-0 h-1 bg-[#17C5B0]" />

            <div className="relative h-full flex flex-col justify-between p-5">
              {/* Top */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-black bg-[#17C5B0]/15 text-[#17C5B0]">
                    M
                  </div>
                  <div>
                    <div className="text-white text-sm font-bold leading-tight">Meridian</div>
                    <div className="text-[9px] uppercase tracking-[0.2em] font-semibold text-[#17C5B0]">
                      Sales Team
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] text-[#A1A1A8] uppercase tracking-wider">Badge</div>
                  <div className="text-xs font-mono font-bold text-white">{rep.badge_number}</div>
                </div>
              </div>

              {/* Middle */}
              <div className="flex items-center gap-4 -mt-1">
                <div className="w-16 h-16 rounded-xl overflow-hidden flex-shrink-0 border border-[#17C5B0]/30">
                  {rep.photo_url ? (
                    <img src={rep.photo_url} alt={rep.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-lg font-bold bg-[#17C5B0]/10 text-[#17C5B0]">
                      {getInitials(rep.name)}
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-white text-lg font-bold leading-tight truncate">{rep.name}</div>
                  <div className="text-sm mt-0.5 truncate text-[#17C5B0]">{rep.title}</div>
                </div>
              </div>

              {/* Bottom */}
              <div className="flex items-end justify-between">
                <div className="space-y-0.5">
                  {rep.email && <div className="text-[11px] text-[#A1A1A8] truncate max-w-[200px]">{rep.email}</div>}
                  {rep.phone && <div className="text-[11px] text-[#A1A1A8]">{rep.phone}</div>}
                </div>
                {qrUrl && (
                  <div className="w-14 h-14 rounded-lg p-1 flex-shrink-0 bg-[#17C5B0]/10">
                    <img src={qrUrl} alt="QR" className="w-full h-full" />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── BACK ── */}
          <div
            className="absolute inset-0 rounded-2xl overflow-hidden shadow-2xl"
            style={{
              backfaceVisibility: 'hidden',
              transform: 'rotateY(180deg)',
              background: 'linear-gradient(135deg, #0d1117 0%, #0a1a2e 40%, #0d2b3e 100%)',
            }}
          >
            <div className="absolute top-0 left-0 right-0 h-1 bg-[#17C5B0]" />
            <div className="relative h-full flex flex-col items-center justify-center p-6 text-center">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-xl font-black bg-[#17C5B0]/10 text-[#17C5B0] mb-2">
                M
              </div>
              <div className="text-white text-lg font-bold">Meridian</div>
              <div className="text-[10px] uppercase tracking-[0.3em] font-semibold mt-1 text-[#17C5B0]">
                Retail Intelligence
              </div>
              {qrUrl && (
                <div className="mt-3 w-24 h-24 rounded-xl p-1.5 bg-[#17C5B0]/10">
                  <img src={qrUrl} alt="QR" className="w-full h-full" />
                </div>
              )}
              <div className="mt-2 text-[11px] text-[#A1A1A8]">meridian.tips</div>
            </div>
          </div>
        </div>
      </div>

      <p className="text-[11px] text-[#A1A1A8] mt-3">Tap card to flip</p>

      {/* Action buttons */}
      <div className="mt-6 w-full max-w-[380px] space-y-2">
        {rep.phone && (
          <a
            href={`tel:${rep.phone}`}
            className="flex items-center gap-3 w-full px-4 py-3 rounded-xl bg-[#111114] border border-[#1F1F23] text-white text-sm font-medium active:bg-[#1F1F23] transition-colors"
          >
            <Phone size={18} className="text-[#17C5B0]" />
            Call {rep.name.split(' ')[0]}
            <span className="ml-auto text-[#A1A1A8] text-xs">{rep.phone}</span>
          </a>
        )}
        {rep.email && (
          <a
            href={`mailto:${rep.email}`}
            className="flex items-center gap-3 w-full px-4 py-3 rounded-xl bg-[#111114] border border-[#1F1F23] text-white text-sm font-medium active:bg-[#1F1F23] transition-colors"
          >
            <Mail size={18} className="text-[#17C5B0]" />
            Email
            <span className="ml-auto text-[#A1A1A8] text-xs truncate max-w-[180px]">{rep.email}</span>
          </a>
        )}
        <button
          onClick={downloadVCard}
          className="flex items-center gap-3 w-full px-4 py-3 rounded-xl bg-[#111114] border border-[#1F1F23] text-white text-sm font-medium active:bg-[#1F1F23] transition-colors"
        >
          <Globe size={18} className="text-[#17C5B0]" />
          Save to Contacts
          <span className="ml-auto text-[#A1A1A8] text-xs">.vcf</span>
        </button>
        <button
          onClick={handleShare}
          className="flex items-center gap-3 w-full px-4 py-3 rounded-xl bg-[#111114] border border-[#1F1F23] text-white text-sm font-medium active:bg-[#1F1F23] transition-colors"
        >
          <Share size={18} className="text-[#17C5B0]" />
          Share Card
        </button>
      </div>

      {/* Add to Home Screen tip */}
      <button
        onClick={() => setShowTip(!showTip)}
        className="mt-6 flex items-center gap-2 text-[#17C5B0] text-xs font-medium"
      >
        <ChevronUp size={14} className={`transition-transform ${showTip ? 'rotate-180' : ''}`} />
        Add to Home Screen for quick access
      </button>
      {showTip && (
        <div className="mt-3 w-full max-w-[380px] bg-[#111114] border border-[#1F1F23] rounded-xl p-4 text-sm text-[#A1A1A8] space-y-2">
          <p className="font-semibold text-white text-xs">iPhone:</p>
          <ol className="list-decimal list-inside space-y-1 text-xs">
            <li>Tap the <span className="text-white font-medium">Share</span> button (box with arrow) in Safari</li>
            <li>Scroll down and tap <span className="text-white font-medium">Add to Home Screen</span></li>
            <li>Tap <span className="text-white font-medium">Add</span> — your badge card appears as an app icon</li>
          </ol>
          <p className="text-[11px] text-[#17C5B0] mt-2">Opens instantly like a wallet card — no browser UI</p>
        </div>
      )}
    </div>
  )
}
