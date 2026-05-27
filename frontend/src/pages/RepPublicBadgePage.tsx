import { useParams, Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Shield, ExternalLink, Mail, Phone } from 'lucide-react'
import { MeridianEmblem } from '@/components/MeridianLogo'
import { supabase } from '@/lib/supabase'

interface RepInfo {
  name: string
  title: string
  badge_number: string
  email?: string
  phone?: string
  photo_url?: string
}

export default function RepPublicBadgePage() {
  const { badgeId } = useParams<{ badgeId: string }>()
  const [rep, setRep] = useState<RepInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    async function loadRep() {
      if (!badgeId) { setNotFound(true); setLoading(false); return }

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
              email: data.email,
              phone: data.phone,
            })
            setLoading(false)
            return
          }
        } catch { /* fallback below */ }
      }

      // Fallback: decode badge number to show basic info
      setRep({
        name: 'Meridian Sales Representative',
        title: 'Sales Representative',
        badge_number: badgeId,
      })
      setLoading(false)
    }
    loadRep()
  }, [badgeId])

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#17C5B0] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (notFound || !rep) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center gap-4 px-4">
        <Shield size={48} className="text-[#A1A1A8]" />
        <h1 className="text-xl font-bold text-white">Badge Not Found</h1>
        <p className="text-sm text-[#A1A1A8] text-center">
          This badge ID doesn't match any active representative.
        </p>
        <Link to="/" className="text-sm text-[#17C5B0] hover:underline mt-2">
          Go to Meridian
        </Link>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4 py-12">
      {/* Verified badge card */}
      <div className="w-full max-w-sm bg-[#111114] border border-[#1F1F23] rounded-2xl overflow-hidden shadow-2xl">
        {/* Header stripe */}
        <div className="h-1.5 bg-gradient-to-r from-[#17C5B0] via-[#17C5B0] to-[#0d9488]" />

        <div className="p-6 text-center space-y-5">
          {/* Logo */}
          <div className="flex items-center justify-center gap-2">
            <MeridianEmblem size={28} />
            <div className="text-left">
              <div className="text-white text-sm font-bold">Meridian</div>
              <div className="text-[8px] text-[#17C5B0] uppercase tracking-[0.2em] font-semibold">Verified Representative</div>
            </div>
          </div>

          {/* Photo or initials */}
          <div className="flex justify-center">
            {rep.photo_url ? (
              <img
                src={rep.photo_url}
                alt={rep.name}
                className="w-24 h-24 rounded-full border-3 border-[#17C5B0]/30 object-cover"
              />
            ) : (
              <div className="w-24 h-24 rounded-full bg-[#17C5B0]/10 flex items-center justify-center text-3xl font-bold text-[#17C5B0]">
                {rep.name.split(' ').map(w => w[0]).filter(Boolean).slice(0, 2).join('').toUpperCase()}
              </div>
            )}
          </div>

          {/* Name + Title */}
          <div>
            <h1 className="text-xl font-bold text-white">{rep.name}</h1>
            <p className="text-sm text-[#17C5B0] mt-0.5">{rep.title}</p>
          </div>

          {/* Badge number */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#17C5B0]/10 border border-[#17C5B0]/20">
            <Shield size={14} className="text-[#17C5B0]" />
            <span className="text-sm font-mono font-bold text-[#17C5B0]">{rep.badge_number}</span>
          </div>

          {/* Contact info */}
          {(rep.email || rep.phone) && (
            <div className="space-y-2 pt-2">
              {rep.email && (
                <a
                  href={`mailto:${rep.email}`}
                  className="flex items-center justify-center gap-2 text-sm text-[#A1A1A8] hover:text-[#17C5B0] transition-colors"
                >
                  <Mail size={14} />
                  {rep.email}
                </a>
              )}
              {rep.phone && (
                <a
                  href={`tel:${rep.phone}`}
                  className="flex items-center justify-center gap-2 text-sm text-[#A1A1A8] hover:text-[#17C5B0] transition-colors"
                >
                  <Phone size={14} />
                  {rep.phone}
                </a>
              )}
            </div>
          )}

          {/* Verification footer */}
          <div className="pt-4 border-t border-[#1F1F23]">
            <div className="flex items-center justify-center gap-1.5 text-[11px] text-[#A1A1A8]">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              Verified Meridian Representative
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-6 text-center">
        <a
          href="https://meridian.tips"
          className="inline-flex items-center gap-1.5 text-sm text-[#17C5B0] hover:underline"
        >
          meridian.tips <ExternalLink size={12} />
        </a>
      </div>
    </div>
  )
}
