import { useState, useRef, useCallback, useEffect } from 'react'
import {
  CreditCard, Upload, Download, Share2, Printer, Camera,
  Sparkles, Check, Loader2, X, Smartphone,
} from 'lucide-react'
import QRCode from 'qrcode'
import html2canvas from 'html2canvas'
import { useSalesAuth } from '@/lib/sales-auth'

const BADGE_COLORS = [
  { name: 'Meridian Teal', bg: 'linear-gradient(135deg, #0d1117 0%, #0a1a2e 40%, #0d2b3e 100%)', accent: '#17C5B0' },
  { name: 'Obsidian', bg: 'linear-gradient(135deg, #0a0a0b 0%, #1a1a2e 40%, #0d0d1a 100%)', accent: '#a78bfa' },
  { name: 'Midnight Blue', bg: 'linear-gradient(135deg, #0c1222 0%, #162447 40%, #1f3c67 100%)', accent: '#60a5fa' },
  { name: 'Carbon', bg: 'linear-gradient(135deg, #111111 0%, #1c1c1c 50%, #2a2a2a 100%)', accent: '#f59e0b' },
]

function generateBadgeNumber(repId: string): string {
  let hash = 0
  for (let i = 0; i < repId.length; i++) {
    hash = repId.charCodeAt(i) + ((hash << 5) - hash)
  }
  const num = Math.abs(hash) % 99999
  return `MRD-${String(num).padStart(5, '0')}`
}

function getInitials(name: string): string {
  return name.split(' ').map(w => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase()
}

export default function USPortalBadgePage() {
  const { rep } = useSalesAuth()
  const cardRef = useRef<HTMLDivElement>(null)

  const [name, setName] = useState(rep?.name || '')
  const [title, setTitle] = useState('Sales Representative')
  const [badgeNumber, setBadgeNumber] = useState(() => generateBadgeNumber(rep?.rep_id || 'demo'))
  const [phone, setPhone] = useState(rep?.phone || '')
  const [email, setEmail] = useState(rep?.email || '')
  const [colorIdx, setColorIdx] = useState(0)

  const [photo, setPhoto] = useState<string | null>(null)
  const [processedPhoto, setProcessedPhoto] = useState<string | null>(null)
  const [processingPhoto, setProcessingPhoto] = useState(false)

  const [qrDataUrl, setQrDataUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [copied, setCopied] = useState(false)

  const badgeUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/rep/${encodeURIComponent(badgeNumber)}`
    : ''

  useEffect(() => {
    if (!badgeUrl) return
    QRCode.toDataURL(badgeUrl, {
      width: 120,
      margin: 1,
      color: { dark: '#ffffff', light: '#00000000' },
      errorCorrectionLevel: 'M',
    }).then(setQrDataUrl).catch(() => {})
  }, [badgeUrl])

  const handlePhotoUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      setPhoto(dataUrl)
      processHeadshot(dataUrl)
    }
    reader.readAsDataURL(file)
  }, [])

  function processHeadshot(src: string) {
    setProcessingPhoto(true)
    setProcessedPhoto(null)

    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const size = 400
      const canvas = document.createElement('canvas')
      canvas.width = size
      canvas.height = size
      const ctx = canvas.getContext('2d')!

      const scale = Math.max(size / img.width, size / img.height)
      const sw = img.width * scale
      const sh = img.height * scale
      const sx = (size - sw) / 2
      const sy = (size - sh) / 2

      // Professional gradient backdrop
      const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size * 0.7)
      grad.addColorStop(0, '#1a2332')
      grad.addColorStop(1, '#0a0f1a')
      ctx.fillStyle = grad
      ctx.fillRect(0, 0, size, size)

      ctx.drawImage(img, sx, sy, sw, sh)

      // Subtle vignette overlay for professional look
      const vignette = ctx.createRadialGradient(size / 2, size / 2, size * 0.3, size / 2, size / 2, size * 0.7)
      vignette.addColorStop(0, 'rgba(0,0,0,0)')
      vignette.addColorStop(1, 'rgba(0,0,0,0.3)')
      ctx.fillStyle = vignette
      ctx.fillRect(0, 0, size, size)

      setProcessedPhoto(canvas.toDataURL('image/jpeg', 0.92))
      setProcessingPhoto(false)
    }
    img.onerror = () => {
      setProcessedPhoto(src)
      setProcessingPhoto(false)
    }
    img.src = src
  }

  async function handleDownload() {
    if (!cardRef.current) return
    setSaving(true)
    try {
      const canvas = await html2canvas(cardRef.current, {
        scale: 3,
        backgroundColor: null,
        useCORS: true,
        logging: false,
      })
      const link = document.createElement('a')
      link.download = `${name.replace(/\s+/g, '-').toLowerCase()}-badge.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
    } catch { /* ignore */ }
    setSaving(false)
  }

  function handlePrint() {
    window.print()
  }

  async function handleShare() {
    if (navigator.share) {
      try {
        await navigator.share({ title: `${name} — Meridian`, url: badgeUrl })
      } catch { /* cancelled */ }
    } else {
      await navigator.clipboard.writeText(badgeUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Persist badge data for wallet card page
  useEffect(() => {
    localStorage.setItem('meridian_badge_data', JSON.stringify({
      name, title, badge_number: badgeNumber, email, phone, photo_url: displayPhoto || undefined,
    }))
  }, [name, title, badgeNumber, email, phone, processedPhoto, photo])

  const walletUrl = `${window.location.origin}/wallet/${encodeURIComponent(badgeNumber)}`

  function downloadVCard() {
    const nameParts = name.split(' ')
    const last = nameParts.length > 1 ? nameParts.pop()! : ''
    const first = nameParts.join(' ')
    const vcf = [
      'BEGIN:VCARD', 'VERSION:3.0',
      `N:${last};${first};;;`, `FN:${name}`,
      `TITLE:${title}`, `ORG:Meridian`,
      phone ? `TEL;TYPE=WORK:${phone}` : '',
      email ? `EMAIL;TYPE=WORK:${email}` : '',
      `URL:https://meridian.tips`, `NOTE:Badge ${badgeNumber}`,
      'END:VCARD',
    ].filter(Boolean).join('\r\n')
    const blob = new Blob([vcf], { type: 'text/vcard;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${name.replace(/\s+/g, '-')}.vcf`
    a.click()
    URL.revokeObjectURL(url)
  }

  const theme = BADGE_COLORS[colorIdx]
  const displayPhoto = processedPhoto || photo

  return (
    <div className="space-y-8 pb-24 print:pb-0">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <CreditCard size={24} className="text-[#17C5B0]" />
          Digital Badge
        </h1>
        <p className="text-sm text-[#A1A1A8] mt-1">
          Create your professional business card with QR code
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Editor Panel */}
        <div className="space-y-6 print:hidden">
          {/* Photo Upload */}
          <div className="bg-[#111114] border border-[#1F1F23] rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Camera size={16} className="text-[#17C5B0]" />
              Profile Photo
            </h3>
            <div className="flex items-center gap-4">
              <div className="relative w-20 h-20 rounded-full overflow-hidden bg-[#1F1F23] border-2 border-[#2A2A2E] flex-shrink-0">
                {processingPhoto ? (
                  <div className="w-full h-full flex items-center justify-center">
                    <Loader2 size={24} className="text-[#17C5B0] animate-spin" />
                  </div>
                ) : displayPhoto ? (
                  <img src={displayPhoto} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-2xl font-bold text-[#A1A1A8]">
                    {getInitials(name)}
                  </div>
                )}
              </div>
              <div className="flex-1 space-y-2">
                <label className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#17C5B0]/10 text-[#17C5B0] text-sm font-medium cursor-pointer hover:bg-[#17C5B0]/20 transition-colors w-fit">
                  <Upload size={16} />
                  Upload Photo
                  <input type="file" accept="image/*" capture="user" className="hidden" onChange={handlePhotoUpload} />
                </label>
                <p className="text-[11px] text-[#A1A1A8]">
                  <Sparkles size={12} className="inline mr-1 text-[#17C5B0]" />
                  Auto-enhanced with professional styling
                </p>
              </div>
              {displayPhoto && (
                <button
                  onClick={() => { setPhoto(null); setProcessedPhoto(null) }}
                  className="p-2 rounded-lg text-[#A1A1A8] hover:text-red-400 hover:bg-red-400/10 transition-colors"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          </div>

          {/* Card Details */}
          <div className="bg-[#111114] border border-[#1F1F23] rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white mb-1">Card Details</h3>

            <div>
              <label className="text-xs text-[#A1A1A8] mb-1 block">Full Name</label>
              <input
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full bg-[#0A0A0B] border border-[#2A2A2E] rounded-lg px-3 py-2.5 text-sm text-white focus:border-[#17C5B0] focus:ring-1 focus:ring-[#17C5B0]/30 outline-none transition-colors"
              />
            </div>
            <div>
              <label className="text-xs text-[#A1A1A8] mb-1 block">Title / Position</label>
              <input
                value={title}
                onChange={e => setTitle(e.target.value)}
                className="w-full bg-[#0A0A0B] border border-[#2A2A2E] rounded-lg px-3 py-2.5 text-sm text-white focus:border-[#17C5B0] focus:ring-1 focus:ring-[#17C5B0]/30 outline-none transition-colors"
                placeholder="Sales Representative"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[#A1A1A8] mb-1 block">Badge Number</label>
                <input
                  value={badgeNumber}
                  onChange={e => setBadgeNumber(e.target.value)}
                  className="w-full bg-[#0A0A0B] border border-[#2A2A2E] rounded-lg px-3 py-2.5 text-sm text-white font-mono focus:border-[#17C5B0] focus:ring-1 focus:ring-[#17C5B0]/30 outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-xs text-[#A1A1A8] mb-1 block">Phone</label>
                <input
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  className="w-full bg-[#0A0A0B] border border-[#2A2A2E] rounded-lg px-3 py-2.5 text-sm text-white focus:border-[#17C5B0] focus:ring-1 focus:ring-[#17C5B0]/30 outline-none transition-colors"
                  placeholder="(555) 123-4567"
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-[#A1A1A8] mb-1 block">Email</label>
              <input
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full bg-[#0A0A0B] border border-[#2A2A2E] rounded-lg px-3 py-2.5 text-sm text-white focus:border-[#17C5B0] focus:ring-1 focus:ring-[#17C5B0]/30 outline-none transition-colors"
              />
            </div>
          </div>

          {/* Color Theme */}
          <div className="bg-[#111114] border border-[#1F1F23] rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-3">Card Theme</h3>
            <div className="flex gap-3">
              {BADGE_COLORS.map((c, i) => (
                <button
                  key={i}
                  onClick={() => setColorIdx(i)}
                  className={`relative w-12 h-12 rounded-xl border-2 transition-all ${
                    i === colorIdx ? 'border-white scale-110' : 'border-[#2A2A2E] hover:border-[#3A3A3E]'
                  }`}
                  style={{ background: c.bg }}
                  title={c.name}
                >
                  {i === colorIdx && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Check size={16} className="text-white drop-shadow" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-3">
            <a
              href={walletUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold hover:bg-[#17C5B0]/90 transition-colors"
            >
              <Smartphone size={16} />
              Add to Phone
            </a>
            <button
              onClick={handleDownload}
              disabled={saving}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1F1F23] text-white text-sm font-medium hover:bg-[#2A2A2E] transition-colors disabled:opacity-50"
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
              Save Image
            </button>
            <button
              onClick={downloadVCard}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1F1F23] text-white text-sm font-medium hover:bg-[#2A2A2E] transition-colors"
            >
              <Share2 size={16} />
              Save to Contacts
            </button>
            <button
              onClick={handlePrint}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1F1F23] text-white text-sm font-medium hover:bg-[#2A2A2E] transition-colors"
            >
              <Printer size={16} />
              Print
            </button>
            <button
              onClick={handleShare}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1F1F23] text-white text-sm font-medium hover:bg-[#2A2A2E] transition-colors"
            >
              {copied ? <Check size={16} className="text-green-400" /> : <Share2 size={16} />}
              {copied ? 'Copied!' : 'Share Link'}
            </button>
          </div>

          {/* Wallet info */}
          <div className="bg-[#111114] border border-[#1F1F23] rounded-xl p-4">
            <div className="flex items-start gap-3">
              <Smartphone size={20} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-white">Add to Home Screen</p>
                <p className="text-xs text-[#A1A1A8] mt-1">
                  Tap "Add to Phone" then use Safari's Share button → "Add to Home Screen" for instant wallet-style access. Your badge card will appear as an app icon on your phone.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Card Preview */}
        <div className="flex flex-col items-center gap-4">
          <p className="text-xs text-[#A1A1A8] uppercase tracking-wider font-semibold print:hidden">Live Preview</p>

          {/* Front of card */}
          <div
            ref={cardRef}
            className="w-full max-w-[400px] aspect-[1.6/1] rounded-2xl overflow-hidden shadow-2xl relative"
            style={{ background: theme.bg }}
          >
            {/* Subtle grid pattern overlay */}
            <div
              className="absolute inset-0 opacity-[0.03]"
              style={{
                backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
                backgroundSize: '20px 20px',
              }}
            />

            {/* Accent top stripe */}
            <div className="absolute top-0 left-0 right-0 h-1" style={{ background: theme.accent }} />

            {/* Content */}
            <div className="relative h-full flex flex-col justify-between p-5">
              {/* Top row: Logo + Badge number */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-black"
                    style={{ background: `${theme.accent}20`, color: theme.accent }}
                  >
                    M
                  </div>
                  <div>
                    <div className="text-white text-sm font-bold leading-tight">Meridian</div>
                    <div className="text-[9px] uppercase tracking-[0.2em] font-semibold" style={{ color: theme.accent }}>
                      Sales Team
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] text-[#A1A1A8] uppercase tracking-wider">Badge</div>
                  <div className="text-xs font-mono font-bold text-white">{badgeNumber}</div>
                </div>
              </div>

              {/* Middle: Photo + Name */}
              <div className="flex items-center gap-4 -mt-1">
                <div
                  className="w-16 h-16 rounded-xl overflow-hidden flex-shrink-0 border"
                  style={{ borderColor: `${theme.accent}40` }}
                >
                  {displayPhoto ? (
                    <img src={displayPhoto} alt={name} className="w-full h-full object-cover" />
                  ) : (
                    <div
                      className="w-full h-full flex items-center justify-center text-lg font-bold"
                      style={{ background: `${theme.accent}15`, color: theme.accent }}
                    >
                      {getInitials(name)}
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-white text-lg font-bold leading-tight truncate">{name || 'Your Name'}</div>
                  <div className="text-sm mt-0.5 truncate" style={{ color: theme.accent }}>{title || 'Position'}</div>
                </div>
              </div>

              {/* Bottom: Contact + QR */}
              <div className="flex items-end justify-between">
                <div className="space-y-0.5">
                  {email && <div className="text-[11px] text-[#A1A1A8] truncate max-w-[200px]">{email}</div>}
                  {phone && <div className="text-[11px] text-[#A1A1A8]">{phone}</div>}
                </div>
                {qrDataUrl && (
                  <div
                    className="w-14 h-14 rounded-lg p-1 flex-shrink-0"
                    style={{ background: `${theme.accent}15` }}
                  >
                    <img src={qrDataUrl} alt="QR Code" className="w-full h-full" />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* QR link info */}
          <div className="text-center print:hidden">
            <p className="text-[11px] text-[#A1A1A8]">
              QR code links to your public profile
            </p>
            <p className="text-[11px] text-[#17C5B0] font-mono mt-0.5 break-all max-w-[300px]">{badgeUrl}</p>
          </div>

          {/* Back of card */}
          <div
            className="w-full max-w-[400px] aspect-[1.6/1] rounded-2xl overflow-hidden shadow-2xl relative mt-4"
            style={{ background: theme.bg }}
          >
            <div className="absolute top-0 left-0 right-0 h-1" style={{ background: theme.accent }} />
            <div
              className="absolute inset-0 opacity-[0.03]"
              style={{
                backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
                backgroundSize: '20px 20px',
              }}
            />
            <div className="relative h-full flex flex-col items-center justify-center p-6 text-center">
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-black mb-3"
                style={{ background: `${theme.accent}15`, color: theme.accent }}
              >
                M
              </div>
              <div className="text-white text-xl font-bold">Meridian</div>
              <div className="text-[10px] uppercase tracking-[0.3em] font-semibold mt-1" style={{ color: theme.accent }}>
                Retail Intelligence Platform
              </div>
              <div className="mt-4 text-[11px] text-[#A1A1A8]">meridian.tips</div>
              {qrDataUrl && (
                <div className="mt-3 w-20 h-20 rounded-xl p-1.5" style={{ background: `${theme.accent}10` }}>
                  <img src={qrDataUrl} alt="QR" className="w-full h-full" />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Print styles */}
      <style>{`
        @media print {
          body * { visibility: hidden !important; }
          [data-badge-printable], [data-badge-printable] * { visibility: visible !important; }
          [data-badge-printable] { position: absolute; top: 0; left: 0; }
        }
      `}</style>
    </div>
  )
}
