import { useState } from 'react'
import { clsx } from 'clsx'
import { Sparkles, MessageSquare, X } from 'lucide-react'
import type { VoicePersonality } from '@/lib/phone-orders-demo-data'

interface Props {
  personality: VoicePersonality
  onChange: (p: VoicePersonality) => void
}

/**
 * Personality configuration panel. Lets merchants customize
 * how the AI agent talks: formality, upselling, humor, custom phrases.
 */
export default function PersonalityPanel({ personality, onChange }: Props) {
  const [newKeyword, setNewKeyword] = useState('')

  function addKeyword() {
    const kw = newKeyword.trim()
    if (!kw || personality.brandKeywords.includes(kw)) return
    onChange({ ...personality, brandKeywords: [...personality.brandKeywords, kw] })
    setNewKeyword('')
  }

  function removeKeyword(kw: string) {
    onChange({ ...personality, brandKeywords: personality.brandKeywords.filter(k => k !== kw) })
  }

  const inputCls = 'w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50'

  return (
    <div className="card p-4 sm:p-5 space-y-5">
      <div className="flex items-center gap-2">
        <Sparkles size={14} className="text-[#7C5CFF]" />
        <h3 className="text-sm font-semibold text-[#F5F5F7]">Agent Personality</h3>
      </div>

      {/* Formality slider */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs text-[#A1A1A8]">Formality</label>
          <span className="text-[10px] text-[#A1A1A8]/60">
            {personality.formality <= 0.3 ? 'Casual' : personality.formality >= 0.7 ? 'Professional' : 'Balanced'}
          </span>
        </div>
        <input
          type="range" min={0} max={1} step={0.1}
          value={personality.formality}
          onChange={e => onChange({ ...personality, formality: parseFloat(e.target.value) })}
          className="w-full accent-[#7C5CFF] h-1"
        />
        <div className="flex justify-between text-[8px] text-[#A1A1A8]/50 mt-0.5">
          <span>Casual</span><span>Professional</span>
        </div>
      </div>

      {/* Upsell aggressiveness */}
      <div>
        <label className="text-xs text-[#A1A1A8] block mb-2">Upsell Style</label>
        <div className="flex gap-2">
          {(['none', 'gentle', 'active'] as const).map(level => (
            <button
              key={level}
              onClick={() => onChange({ ...personality, upsell: level })}
              className={clsx(
                'flex-1 py-2 rounded-lg border text-xs font-medium capitalize transition-all',
                personality.upsell === level
                  ? 'border-[#7C5CFF]/30 bg-[#7C5CFF]/5 text-[#7C5CFF]'
                  : 'border-[#1F1F23] text-[#A1A1A8] hover:border-[#2A2A30]',
              )}
            >
              {level}
            </button>
          ))}
        </div>
        <p className="text-[9px] text-[#A1A1A8]/50 mt-1">
          {personality.upsell === 'none' ? 'Agent will not suggest additional items.' :
           personality.upsell === 'gentle' ? 'Agent occasionally suggests drinks or desserts.' :
           'Agent actively recommends add-ons and combos.'}
        </p>
      </div>

      {/* Humor toggle */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-[#F5F5F7]">Light Humor</p>
          <p className="text-[10px] text-[#A1A1A8]">Agent occasionally makes friendly jokes</p>
        </div>
        <button
          onClick={() => onChange({ ...personality, humor: !personality.humor })}
          className={clsx(
            'relative w-10 h-5 rounded-full transition-colors',
            personality.humor ? 'bg-[#7C5CFF]' : 'bg-[#2A2A30]',
          )}
        >
          <span className={clsx(
            'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform',
            personality.humor ? 'left-5' : 'left-0.5',
          )} />
        </button>
      </div>

      {/* Custom phrases */}
      <div className="space-y-3 pt-2 border-t border-[#1F1F23]">
        <div className="flex items-center gap-2">
          <MessageSquare size={12} className="text-[#A1A1A8]" />
          <label className="text-xs text-[#A1A1A8] font-medium">Custom Phrases</label>
        </div>

        <div>
          <label className="text-[10px] text-[#A1A1A8] block mb-1">Custom Greeting</label>
          <input
            className={inputCls}
            placeholder="e.g. Welcome to the family!"
            value={personality.customGreeting}
            onChange={e => onChange({ ...personality, customGreeting: e.target.value })}
          />
        </div>

        <div>
          <label className="text-[10px] text-[#A1A1A8] block mb-1">Hold Message</label>
          <input
            className={inputCls}
            placeholder="e.g. Just a moment while I check on that..."
            value={personality.customHold}
            onChange={e => onChange({ ...personality, customHold: e.target.value })}
          />
        </div>

        <div>
          <label className="text-[10px] text-[#A1A1A8] block mb-1">Closing Phrase</label>
          <input
            className={inputCls}
            placeholder="e.g. Enjoy your meal!"
            value={personality.customClosing}
            onChange={e => onChange({ ...personality, customClosing: e.target.value })}
          />
        </div>
      </div>

      {/* Brand keywords */}
      <div className="space-y-2 pt-2 border-t border-[#1F1F23]">
        <label className="text-xs text-[#A1A1A8]">Brand Keywords</label>
        <p className="text-[9px] text-[#A1A1A8]/50">Words the agent weaves into conversation naturally</p>

        {personality.brandKeywords.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {personality.brandKeywords.map(kw => (
              <span key={kw} className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#7C5CFF]/10 text-[#7C5CFF] rounded-full text-[10px] font-medium">
                {kw}
                <button onClick={() => removeKeyword(kw)} className="hover:text-white transition-colors">
                  <X size={10} />
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <input
            className={inputCls + ' flex-1'}
            placeholder="e.g. homemade, fresh-baked, artisan"
            value={newKeyword}
            onChange={e => setNewKeyword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addKeyword()}
          />
          <button
            onClick={addKeyword}
            className="px-3 py-2 bg-[#7C5CFF]/10 text-[#7C5CFF] text-xs font-medium rounded-lg hover:bg-[#7C5CFF]/20 transition-colors"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  )
}
