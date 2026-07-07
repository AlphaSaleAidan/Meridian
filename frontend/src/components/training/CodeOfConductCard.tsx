import { useState } from 'react'
import { FileSignature, ShieldCheck } from 'lucide-react'
import type { SalesRepProfile } from '@/lib/sales-auth'
import { signConduct, type ConductSignature } from '@/lib/training-progress'
import { CODE_OF_CONDUCT, CONDUCT_ACKNOWLEDGEMENT, CONDUCT_VERSION } from './course-data'

/**
 * Final course step: the Meridian Code of Conduct — what reps may never claim
 * or say — signed with a typed full name. Signatures are immutable rows in
 * rep_conduct_signatures, one per conduct version.
 */
export default function CodeOfConductCard({
  rep,
  signature,
  signedCurrent,
  accent,
  onSigned,
}: {
  rep: SalesRepProfile
  signature: ConductSignature | null
  signedCurrent: boolean
  accent: string
  onSigned: () => void
}) {
  const [name, setName] = useState('')
  const [agreed, setAgreed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSign = async () => {
    if (!agreed || name.trim().length < 2 || saving) return
    setSaving(true)
    setError('')
    try {
      await signConduct(rep, name)
      onSigned()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save your signature — try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-[11px] text-white/40">
        Version {CONDUCT_VERSION}. This protects the merchants, you, and Meridian — it is the
        boundary between selling hard and selling something we can't stand behind.
      </p>

      <div className="max-h-80 space-y-4 overflow-y-auto rounded-lg border border-white/10 bg-white/[0.02] p-4">
        {CODE_OF_CONDUCT.map(section => (
          <div key={section.title}>
            <h3 className="text-[12px] font-bold text-white/90 mb-1.5">{section.title}</h3>
            <ul className="space-y-1.5">
              {section.rules.map((rule, i) => (
                <li key={i} className="flex gap-2 text-[11.5px] leading-relaxed text-white/60">
                  <span className="mt-[3px] h-1 w-1 shrink-0 rounded-full" style={{ backgroundColor: accent }} />
                  <span>{rule}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {signedCurrent && signature ? (
        <div className="flex items-center gap-2.5 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3">
          <ShieldCheck size={18} style={{ color: accent }} />
          <div>
            <p className="text-[12px] font-medium text-white/90">
              Signed by {signature.signed_name}
            </p>
            <p className="text-[10.5px] text-white/40">
              {new Date(signature.signed_at).toLocaleDateString()} · version {signature.conduct_version}
            </p>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4 space-y-3">
          <label className="flex items-start gap-2 text-[11.5px] leading-relaxed text-white/70">
            <input
              type="checkbox"
              checked={agreed}
              onChange={e => setAgreed(e.target.checked)}
              className="mt-0.5 accent-current"
            />
            <span>{CONDUCT_ACKNOWLEDGEMENT}</span>
          </label>
          <div>
            <label htmlFor="conduct-signed-name" className="block text-[10.5px] text-white/40 mb-1">
              Type your full legal name to sign
            </label>
            <input
              id="conduct-signed-name"
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={rep.name}
              className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white placeholder-white/25 focus:border-white/30 focus:outline-none"
            />
          </div>
          {error && <p className="text-[11px] text-amber-400">{error}</p>}
          <button
            type="button"
            onClick={handleSign}
            disabled={!agreed || name.trim().length < 2 || saving}
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg px-4 py-2.5 text-xs font-semibold text-black transition-opacity disabled:opacity-40"
            style={{ backgroundColor: accent }}
          >
            <FileSignature size={14} />
            {saving ? 'Signing…' : 'Sign the Code of Conduct'}
          </button>
        </div>
      )}
    </div>
  )
}
