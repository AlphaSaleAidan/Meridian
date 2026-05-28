import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence, Reorder } from 'framer-motion'
import {
  Plus,
  Trash2,
  Copy,
  Play,
  Pause,
  GripVertical,
  Wand2,
  Film,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronRight,
  User,
  Palette,
  Layers,
  Eye,
  Zap,
  Loader2,
  Download,
  Check,
  Settings2,
  Image as ImageIcon,
  Video,
  Type,
  Music,
  Instagram,
  Facebook,
  Music2,
  Coins,
  Lock,
  RefreshCw,
  Maximize2,
  Minimize2,
} from 'lucide-react'
import { contentApi } from '@/lib/content-api'

// ── Types ─────────────────────────────────────────────────────────────────

interface Scene {
  id: string
  prompt: string
  duration: number
  style: string
  transition: 'cut' | 'dissolve' | 'fade' | 'wipe'
  notes: string
}

interface RecurringElement {
  id: string
  type: 'character' | 'object' | 'setting' | 'style'
  name: string
  description: string
  color: string
}

interface BrandData {
  business_name: string
  business_type: string
  voice_profile?: {
    tone?: string
    emoji_usage?: string
    top_products?: string[]
    keywords?: string[]
  }
}

interface Props {
  isDemo: boolean
  creditBalance: number
  merchantId: string
  brand?: BrandData | null
  onBack: () => void
}

type EditorView = 'storyboard' | 'timeline'

// ── Constants ──────────────────────────────────────────────────────────────

const SCENE_STYLES = [
  { id: 'cinematic', label: 'Cinematic', color: '#7C5CFF' },
  { id: 'viral', label: 'Viral', color: '#FF6B6B' },
  { id: 'elegant', label: 'Elegant', color: '#F5C542' },
  { id: 'appetizing', label: 'Appetizing', color: '#FF8C42' },
  { id: 'energetic', label: 'Energetic', color: '#42C6FF' },
  { id: 'professional', label: 'Professional', color: '#4CAF50' },
  { id: 'raw', label: 'Raw/Authentic', color: '#A1A1A8' },
]

const TRANSITIONS = [
  { id: 'cut' as const, label: 'Cut', desc: 'Hard cut' },
  { id: 'dissolve' as const, label: 'Dissolve', desc: 'Cross dissolve' },
  { id: 'fade' as const, label: 'Fade', desc: 'Fade through black' },
  { id: 'wipe' as const, label: 'Wipe', desc: 'Directional wipe' },
]

const ELEMENT_COLORS = ['#7C5CFF', '#FF6B6B', '#42C6FF', '#4CAF50', '#FF8C42', '#F5C542', '#FF42A1', '#A1A1A8']

function makeId() {
  return Math.random().toString(36).slice(2, 8)
}

function defaultScene(index: number): Scene {
  return {
    id: makeId(),
    prompt: '',
    duration: index === 0 ? 3 : 4,
    style: 'cinematic',
    transition: 'cut',
    notes: '',
  }
}

// ── Scene Card ─────────────────────────────────────────────────────────────

function SceneCard({
  scene,
  index,
  isSelected,
  elements,
  onSelect,
  onUpdate,
  onDuplicate,
  onDelete,
  canDelete,
}: {
  scene: Scene
  index: number
  isSelected: boolean
  elements: RecurringElement[]
  onSelect: () => void
  onUpdate: (patch: Partial<Scene>) => void
  onDuplicate: () => void
  onDelete: () => void
  canDelete: boolean
}) {
  const styleObj = SCENE_STYLES.find(s => s.id === scene.style) || SCENE_STYLES[0]

  return (
    <Reorder.Item value={scene} id={scene.id}>
      <motion.div
        layout
        onClick={onSelect}
        className={`group relative rounded-lg border transition-all cursor-pointer ${
          isSelected
            ? 'border-[#7C5CFF]/50 bg-[#7C5CFF]/5 shadow-lg shadow-[#7C5CFF]/5'
            : 'border-[#1F1F23] bg-[#131316] hover:border-[#1F1F23]/80'
        }`}
      >
        {/* Scene Header */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-[#1F1F23]/50">
          <GripVertical size={12} className="text-[#A1A1A8]/30 cursor-grab active:cursor-grabbing" />
          <div
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ backgroundColor: styleObj.color }}
          />
          <span className="text-[10px] font-bold text-[#A1A1A8] uppercase tracking-wider">
            Scene {index + 1}
          </span>
          <span className="text-[9px] text-[#A1A1A8]/50 ml-auto">
            {scene.duration}s
          </span>
          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={e => { e.stopPropagation(); onDuplicate() }}
              className="p-1 rounded hover:bg-[#1F1F23] transition-colors"
              title="Duplicate scene"
            >
              <Copy size={10} className="text-[#A1A1A8]" />
            </button>
            {canDelete && (
              <button
                onClick={e => { e.stopPropagation(); onDelete() }}
                className="p-1 rounded hover:bg-red-500/10 transition-colors"
                title="Delete scene"
              >
                <Trash2 size={10} className="text-red-400/60" />
              </button>
            )}
          </div>
        </div>

        {/* Scene Body */}
        <div className="p-3 space-y-2">
          <textarea
            value={scene.prompt}
            onChange={e => onUpdate({ prompt: e.target.value })}
            onClick={e => e.stopPropagation()}
            placeholder={index === 0
              ? "Opening hook — what grabs attention in the first 2 seconds?"
              : `Scene ${index + 1} — describe the action, camera, lighting...`
            }
            rows={2}
            className="w-full bg-transparent text-[11px] text-[#F5F5F7] placeholder:text-[#A1A1A8]/25 resize-none focus:outline-none"
          />

          {/* Element Tags */}
          {elements.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {elements.map(el => (
                <span
                  key={el.id}
                  className="text-[8px] font-medium px-1.5 py-0.5 rounded-full border"
                  style={{
                    color: el.color,
                    borderColor: el.color + '30',
                    backgroundColor: el.color + '10',
                  }}
                >
                  {el.name}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Transition indicator */}
        {scene.transition !== 'cut' && (
          <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 z-10">
            <span className="text-[8px] font-medium text-[#A1A1A8]/40 bg-[#0A0A0B] px-1.5 py-0.5 rounded border border-[#1F1F23]/30">
              {scene.transition}
            </span>
          </div>
        )}
      </motion.div>
    </Reorder.Item>
  )
}

// ── Timeline Bar ───────────────────────────────────────────────────────────

function TimelineBar({
  scenes,
  selectedId,
  onSelect,
}: {
  scenes: Scene[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const totalDuration = scenes.reduce((s, sc) => s + sc.duration, 0)

  return (
    <div className="relative h-12 bg-[#0A0A0B] rounded-lg border border-[#1F1F23] overflow-hidden flex">
      {scenes.map((scene, i) => {
        const pct = (scene.duration / totalDuration) * 100
        const styleObj = SCENE_STYLES.find(s => s.id === scene.style) || SCENE_STYLES[0]
        const isSelected = scene.id === selectedId

        return (
          <button
            key={scene.id}
            onClick={() => onSelect(scene.id)}
            className={`relative h-full transition-all ${
              isSelected ? 'ring-1 ring-[#7C5CFF] z-10' : 'hover:brightness-110'
            }`}
            style={{
              width: `${pct}%`,
              backgroundColor: styleObj.color + (isSelected ? '30' : '15'),
              borderRight: i < scenes.length - 1 ? '1px solid #1F1F23' : 'none',
            }}
          >
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-[9px] font-bold text-[#F5F5F7]/70">{i + 1}</span>
            </div>
            <div className="absolute bottom-0.5 right-1">
              <span className="text-[7px] text-[#A1A1A8]/40">{scene.duration}s</span>
            </div>
          </button>
        )
      })}

      {/* Playhead line */}
      <div className="absolute top-0 bottom-0 left-0 w-px bg-[#F5F5F7]/20" />

      {/* Total duration */}
      <div className="absolute top-1 right-2 text-[8px] text-[#A1A1A8]/40 font-mono">
        {totalDuration}s total
      </div>
    </div>
  )
}

// ── Inspector Panel ────────────────────────────────────────────────────────

function InspectorPanel({
  scene,
  elements,
  onUpdate,
  onToggleElement,
}: {
  scene: Scene
  elements: RecurringElement[]
  onUpdate: (patch: Partial<Scene>) => void
  onToggleElement: (elementId: string) => void
}) {
  const [showTransitions, setShowTransitions] = useState(false)

  return (
    <div className="space-y-4">
      {/* Style */}
      <div>
        <label className="text-[10px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
          Scene Style
        </label>
        <div className="grid grid-cols-2 gap-1.5">
          {SCENE_STYLES.map(s => (
            <button
              key={s.id}
              onClick={() => onUpdate({ style: s.id })}
              className={`flex items-center gap-2 px-2.5 py-2 rounded-md border text-[10px] font-medium transition-all ${
                scene.style === s.id
                  ? 'border-[#7C5CFF]/40 bg-[#7C5CFF]/10 text-[#F5F5F7]'
                  : 'border-[#1F1F23] text-[#A1A1A8] hover:border-[#1F1F23]/80'
              }`}
            >
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} />
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Duration */}
      <div>
        <label className="text-[10px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
          Duration: {scene.duration}s
        </label>
        <input
          type="range"
          min={2}
          max={10}
          value={scene.duration}
          onChange={e => onUpdate({ duration: Number(e.target.value) })}
          className="w-full accent-[#7C5CFF]"
        />
        <div className="flex justify-between text-[8px] text-[#A1A1A8]/40 mt-0.5">
          <span>2s</span>
          <span>10s</span>
        </div>
      </div>

      {/* Transition */}
      <div>
        <button
          onClick={() => setShowTransitions(!showTransitions)}
          className="flex items-center gap-1.5 text-[10px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2"
        >
          {showTransitions ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          Transition Out
        </button>
        {showTransitions && (
          <div className="grid grid-cols-2 gap-1.5">
            {TRANSITIONS.map(t => (
              <button
                key={t.id}
                onClick={() => onUpdate({ transition: t.id })}
                className={`px-2.5 py-1.5 rounded-md border text-[10px] transition-all ${
                  scene.transition === t.id
                    ? 'border-[#7C5CFF]/40 bg-[#7C5CFF]/10 text-[#F5F5F7]'
                    : 'border-[#1F1F23] text-[#A1A1A8] hover:border-[#1F1F23]/80'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Elements in this scene */}
      {elements.length > 0 && (
        <div>
          <label className="text-[10px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
            Elements
          </label>
          <div className="space-y-1">
            {elements.map(el => (
              <button
                key={el.id}
                onClick={() => onToggleElement(el.id)}
                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-md border border-[#1F1F23] hover:border-[#1F1F23]/80 text-left transition-colors"
              >
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: el.color }} />
                <span className="text-[10px] text-[#F5F5F7] flex-1">{el.name}</span>
                <span className="text-[8px] text-[#A1A1A8]/40 capitalize">{el.type}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Notes */}
      <div>
        <label className="text-[10px] font-medium text-[#A1A1A8] uppercase tracking-wider mb-2 block">
          Director Notes
        </label>
        <textarea
          value={scene.notes}
          onChange={e => onUpdate({ notes: e.target.value })}
          placeholder="Camera angles, lighting cues, mood references..."
          rows={2}
          className="w-full bg-[#0A0A0B] border border-[#1F1F23] rounded-md px-3 py-2 text-[10px] text-[#F5F5F7] placeholder:text-[#A1A1A8]/25 resize-none focus:outline-none focus:border-[#7C5CFF]/30"
        />
      </div>
    </div>
  )
}

// ── Main Workshop Editor ───────────────────────────────────────────────────

export default function WorkshopEditor({ isDemo, creditBalance, merchantId, brand, onBack }: Props) {
  const [scenes, setScenes] = useState<Scene[]>([
    { ...defaultScene(0), prompt: '' },
    { ...defaultScene(1), prompt: '' },
    { ...defaultScene(2), prompt: '' },
  ])
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(scenes[0].id)
  const [elements, setElements] = useState<RecurringElement[]>([])
  const [view, setView] = useState<EditorView>('storyboard')
  const [showElementPanel, setShowElementPanel] = useState(false)
  const [projectName, setProjectName] = useState('Untitled Commercial')
  const [platform, setPlatform] = useState('instagram_reel')
  const [generating, setGenerating] = useState(false)
  const [genStatus, setGenStatus] = useState('')
  const [expandedInspector, setExpandedInspector] = useState(true)
  const [showNewElement, setShowNewElement] = useState(false)
  const [newElement, setNewElement] = useState({ name: '', description: '', type: 'character' as RecurringElement['type'] })

  const selectedScene = scenes.find(s => s.id === selectedSceneId) || null
  const totalDuration = scenes.reduce((s, sc) => s + sc.duration, 0)
  const totalScenes = scenes.length

  const updateScene = useCallback((id: string, patch: Partial<Scene>) => {
    setScenes(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s))
  }, [])

  const addScene = useCallback(() => {
    const newScene = defaultScene(scenes.length)
    setScenes(prev => [...prev, newScene])
    setSelectedSceneId(newScene.id)
  }, [scenes.length])

  const duplicateScene = useCallback((id: string) => {
    setScenes(prev => {
      const idx = prev.findIndex(s => s.id === id)
      if (idx === -1) return prev
      const clone = { ...prev[idx], id: makeId(), prompt: prev[idx].prompt }
      const next = [...prev]
      next.splice(idx + 1, 0, clone)
      return next
    })
  }, [])

  const deleteScene = useCallback((id: string) => {
    setScenes(prev => {
      if (prev.length <= 1) return prev
      const filtered = prev.filter(s => s.id !== id)
      if (selectedSceneId === id) {
        setSelectedSceneId(filtered[0]?.id ?? null)
      }
      return filtered
    })
  }, [selectedSceneId])

  const addElement = useCallback(() => {
    if (!newElement.name.trim()) return
    const el: RecurringElement = {
      id: makeId(),
      type: newElement.type,
      name: newElement.name.trim(),
      description: newElement.description.trim(),
      color: ELEMENT_COLORS[elements.length % ELEMENT_COLORS.length],
    }
    setElements(prev => [...prev, el])
    setNewElement({ name: '', description: '', type: 'character' })
    setShowNewElement(false)
  }, [newElement, elements.length])

  const removeElement = useCallback((id: string) => {
    setElements(prev => prev.filter(e => e.id !== id))
  }, [])

  const buildFullPrompt = useCallback(() => {
    const parts: string[] = []

    if (elements.length > 0) {
      const elDesc = elements.map(el => `${el.name} (${el.type}): ${el.description}`).join('; ')
      parts.push(`Recurring elements: ${elDesc}.`)
    }

    scenes.forEach((sc, i) => {
      if (!sc.prompt.trim()) return
      const styleLabel = SCENE_STYLES.find(s => s.id === sc.style)?.label || sc.style
      let line = `[Scene ${i + 1}, ${sc.duration}s, ${styleLabel}]`
      if (sc.transition !== 'cut' && i < scenes.length - 1) {
        line += ` (transition: ${sc.transition})`
      }
      line += ` ${sc.prompt.trim()}`
      if (sc.notes.trim()) {
        line += ` — Note: ${sc.notes.trim()}`
      }
      parts.push(line)
    })

    return parts.join('\n')
  }, [scenes, elements])

  const handleGenerate = async () => {
    if (isDemo) return
    const filledScenes = scenes.filter(s => s.prompt.trim())
    if (filledScenes.length === 0) return

    setGenerating(true)
    setGenStatus('Building commercial prompt...')

    try {
      const fullPrompt = buildFullPrompt()
      const brandPayload = brand ? {
        business_name: brand.business_name,
        business_type: brand.business_type,
        voice_profile: brand.voice_profile ?? {},
      } : undefined

      setGenStatus(brand ? 'Director enhancing commercial...' : 'Submitting to AI...')

      const res = await contentApi.generateVideo(merchantId, {
        prompt: fullPrompt,
        platform,
        model: 'seedance-2',
        style: scenes[0]?.style || 'cinematic',
        durationSeconds: Math.min(totalDuration, 10),
        brand: brandPayload,
        enhance: !!brand,
      })

      if (!res.jobId) {
        setGenStatus('Complete!')
        setGenerating(false)
        return
      }

      setGenStatus('Generating commercial...')
      for (let i = 0; i < 180; i++) {
        await new Promise(r => setTimeout(r, 3000))
        const status = await contentApi.videoStatus(res.jobId)
        const elapsed = Math.round(status.elapsed ?? i * 3)
        setGenStatus(`Rendering... ${elapsed}s (${status.fal_status ?? 'processing'})`)

        if (status.status === 'completed') {
          setGenStatus('Commercial complete!')
          setGenerating(false)
          return
        }
        if (status.status === 'failed') {
          throw new Error(status.error ?? 'Generation failed')
        }
      }
    } catch (err) {
      setGenStatus(err instanceof Error ? err.message : 'Generation failed')
      setGenerating(false)
    }
  }

  const PLATFORMS = [
    { id: 'instagram_reel', label: 'IG Reels', icon: Instagram, aspect: '9:16' },
    { id: 'tiktok', label: 'TikTok', icon: Music2, aspect: '9:16' },
    { id: 'facebook', label: 'Facebook', icon: Facebook, aspect: '16:9' },
    { id: 'instagram_feed', label: 'IG Feed', icon: Instagram, aspect: '1:1' },
  ]

  return (
    <div className="space-y-0">
      {/* ── Top Bar (FCPX-style) ────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#131316] border-b border-[#1F1F23] rounded-t-lg -mb-px">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="text-[10px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
          >
            ← Back
          </button>
          <div className="w-px h-4 bg-[#1F1F23]" />
          <input
            value={projectName}
            onChange={e => setProjectName(e.target.value)}
            className="bg-transparent text-sm font-semibold text-[#F5F5F7] focus:outline-none border-b border-transparent hover:border-[#1F1F23] focus:border-[#7C5CFF]/40 transition-colors"
          />
          <span className="text-[9px] text-[#A1A1A8]/40 font-mono">
            {totalScenes} scenes · {totalDuration}s
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* View Toggle */}
          <div className="flex items-center bg-[#0A0A0B] rounded-md border border-[#1F1F23] p-0.5">
            <button
              onClick={() => setView('storyboard')}
              className={`px-2.5 py-1 rounded text-[9px] font-medium transition-colors ${
                view === 'storyboard' ? 'bg-[#7C5CFF]/20 text-[#7C5CFF]' : 'text-[#A1A1A8] hover:text-[#F5F5F7]'
              }`}
            >
              <Layers size={10} className="inline mr-1" />
              Storyboard
            </button>
            <button
              onClick={() => setView('timeline')}
              className={`px-2.5 py-1 rounded text-[9px] font-medium transition-colors ${
                view === 'timeline' ? 'bg-[#7C5CFF]/20 text-[#7C5CFF]' : 'text-[#A1A1A8] hover:text-[#F5F5F7]'
              }`}
            >
              <Film size={10} className="inline mr-1" />
              Timeline
            </button>
          </div>

          {/* Platform */}
          <select
            value={platform}
            onChange={e => setPlatform(e.target.value)}
            className="bg-[#0A0A0B] border border-[#1F1F23] rounded-md px-2 py-1 text-[10px] text-[#F5F5F7] focus:outline-none focus:border-[#7C5CFF]/30"
          >
            {PLATFORMS.map(p => (
              <option key={p.id} value={p.id}>{p.label} ({p.aspect})</option>
            ))}
          </select>

          <div className="flex items-center gap-1.5 text-[10px] text-[#A1A1A8]">
            <Coins size={10} className="text-amber-400" />
            {creditBalance}
          </div>
        </div>
      </div>

      {/* ── Main Editor Area ────────────────────────────────────────────── */}
      <div className="flex border border-[#1F1F23] border-t-0 rounded-b-lg overflow-hidden bg-[#0A0A0B]" style={{ minHeight: '520px' }}>
        {/* Left: Elements Panel (collapsible) */}
        <AnimatePresence>
          {showElementPanel && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 200, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="border-r border-[#1F1F23] bg-[#131316] overflow-hidden flex-shrink-0"
            >
              <div className="p-3 space-y-3 w-[200px]">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-[#A1A1A8] uppercase tracking-wider">
                    Elements
                  </span>
                  <button
                    onClick={() => setShowNewElement(!showNewElement)}
                    className="p-1 rounded hover:bg-[#1F1F23] transition-colors"
                  >
                    <Plus size={12} className="text-[#7C5CFF]" />
                  </button>
                </div>

                {/* New Element Form */}
                <AnimatePresence>
                  {showNewElement && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="space-y-2 p-2 bg-[#0A0A0B] rounded-md border border-[#1F1F23]">
                        <select
                          value={newElement.type}
                          onChange={e => setNewElement(prev => ({ ...prev, type: e.target.value as RecurringElement['type'] }))}
                          className="w-full bg-transparent border border-[#1F1F23] rounded px-2 py-1 text-[10px] text-[#F5F5F7] focus:outline-none"
                        >
                          <option value="character">Character</option>
                          <option value="object">Object/Product</option>
                          <option value="setting">Setting</option>
                          <option value="style">Style Element</option>
                        </select>
                        <input
                          value={newElement.name}
                          onChange={e => setNewElement(prev => ({ ...prev, name: e.target.value }))}
                          placeholder="Name"
                          className="w-full bg-transparent border border-[#1F1F23] rounded px-2 py-1 text-[10px] text-[#F5F5F7] placeholder:text-[#A1A1A8]/25 focus:outline-none"
                        />
                        <input
                          value={newElement.description}
                          onChange={e => setNewElement(prev => ({ ...prev, description: e.target.value }))}
                          placeholder="Visual description..."
                          className="w-full bg-transparent border border-[#1F1F23] rounded px-2 py-1 text-[10px] text-[#F5F5F7] placeholder:text-[#A1A1A8]/25 focus:outline-none"
                        />
                        <button
                          onClick={addElement}
                          disabled={!newElement.name.trim()}
                          className="w-full py-1 rounded text-[9px] font-medium bg-[#7C5CFF]/20 text-[#7C5CFF] hover:bg-[#7C5CFF]/30 disabled:opacity-30 transition-colors"
                        >
                          Add Element
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Elements List */}
                <div className="space-y-1">
                  {elements.length === 0 ? (
                    <p className="text-[9px] text-[#A1A1A8]/30 text-center py-4">
                      Add recurring characters, products, or settings that appear across scenes
                    </p>
                  ) : (
                    elements.map(el => {
                      const typeIcon = el.type === 'character' ? User
                        : el.type === 'object' ? Palette
                        : el.type === 'setting' ? ImageIcon
                        : Sparkles
                      const Icon = typeIcon
                      return (
                        <div
                          key={el.id}
                          className="group flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-[#1F1F23]/50 transition-colors"
                        >
                          <div
                            className="w-5 h-5 rounded flex items-center justify-center flex-shrink-0"
                            style={{ backgroundColor: el.color + '20' }}
                          >
                            <Icon size={10} style={{ color: el.color }} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-[10px] font-medium text-[#F5F5F7] truncate">{el.name}</p>
                            <p className="text-[8px] text-[#A1A1A8]/40 truncate">{el.description || el.type}</p>
                          </div>
                          <button
                            onClick={() => removeElement(el.id)}
                            className="p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/10 transition-all"
                          >
                            <Trash2 size={8} className="text-red-400/60" />
                          </button>
                        </div>
                      )
                    })
                  )}
                </div>

                {/* Quick-add suggestions based on brand */}
                {brand && elements.length === 0 && (
                  <div className="space-y-1">
                    <span className="text-[8px] text-[#A1A1A8]/30 uppercase tracking-wider">Quick add from brand</span>
                    {(brand.voice_profile?.top_products || []).slice(0, 3).map((prod, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          const el: RecurringElement = {
                            id: makeId(),
                            type: 'object',
                            name: prod,
                            description: `Signature product from ${brand.business_name}`,
                            color: ELEMENT_COLORS[i % ELEMENT_COLORS.length],
                          }
                          setElements(prev => [...prev, el])
                        }}
                        className="w-full text-left px-2 py-1 rounded text-[9px] text-[#A1A1A8] hover:bg-[#1F1F23]/50 transition-colors"
                      >
                        + {prod}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Center: Scene Editor */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Toolbar */}
          <div className="flex items-center gap-1.5 px-3 py-2 border-b border-[#1F1F23] bg-[#131316]/50">
            <button
              onClick={() => setShowElementPanel(!showElementPanel)}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[9px] font-medium transition-colors ${
                showElementPanel ? 'bg-[#7C5CFF]/10 text-[#7C5CFF]' : 'text-[#A1A1A8] hover:text-[#F5F5F7]'
              }`}
            >
              <User size={10} />
              Elements {elements.length > 0 && `(${elements.length})`}
            </button>
            <div className="w-px h-4 bg-[#1F1F23]" />
            <button
              onClick={addScene}
              className="flex items-center gap-1 px-2 py-1 rounded text-[9px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23]/50 transition-colors"
            >
              <Plus size={10} />
              Add Scene
            </button>
            <button
              className="flex items-center gap-1 px-2 py-1 rounded text-[9px] font-medium text-[#A1A1A8] hover:text-[#7C5CFF] hover:bg-[#7C5CFF]/5 transition-colors"
              title="AI auto-fill all scenes from a single concept"
            >
              <Wand2 size={10} />
              Auto-fill
            </button>

            <div className="ml-auto flex items-center gap-1.5">
              <button
                onClick={() => setExpandedInspector(!expandedInspector)}
                className="p-1 rounded text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23]/50 transition-colors"
                title={expandedInspector ? 'Collapse inspector' : 'Expand inspector'}
              >
                {expandedInspector ? <Minimize2 size={10} /> : <Maximize2 size={10} />}
              </button>
            </div>
          </div>

          {/* Scene Grid / Storyboard */}
          <div className="flex-1 overflow-y-auto p-4">
            {view === 'storyboard' ? (
              <div className="flex gap-3 flex-wrap">
                <Reorder.Group
                  axis="x"
                  values={scenes}
                  onReorder={setScenes}
                  className="flex gap-3 flex-wrap"
                >
                  {scenes.map((scene, i) => (
                    <div key={scene.id} className="w-[220px] flex-shrink-0">
                      <SceneCard
                        scene={scene}
                        index={i}
                        isSelected={scene.id === selectedSceneId}
                        elements={elements}
                        onSelect={() => setSelectedSceneId(scene.id)}
                        onUpdate={patch => updateScene(scene.id, patch)}
                        onDuplicate={() => duplicateScene(scene.id)}
                        onDelete={() => deleteScene(scene.id)}
                        canDelete={scenes.length > 1}
                      />
                    </div>
                  ))}
                </Reorder.Group>

                {/* Add Scene Card */}
                <button
                  onClick={addScene}
                  className="w-[220px] flex-shrink-0 h-[140px] rounded-lg border-2 border-dashed border-[#1F1F23] hover:border-[#7C5CFF]/30 flex flex-col items-center justify-center gap-2 transition-colors group"
                >
                  <Plus size={20} className="text-[#A1A1A8]/30 group-hover:text-[#7C5CFF]/50 transition-colors" />
                  <span className="text-[10px] text-[#A1A1A8]/30 group-hover:text-[#A1A1A8]/60 transition-colors">
                    Add Scene
                  </span>
                </button>
              </div>
            ) : (
              /* Timeline View */
              <div className="space-y-3">
                <TimelineBar
                  scenes={scenes}
                  selectedId={selectedSceneId}
                  onSelect={setSelectedSceneId}
                />
                {selectedScene && (
                  <div className="card p-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded"
                        style={{ backgroundColor: (SCENE_STYLES.find(s => s.id === selectedScene.style) || SCENE_STYLES[0]).color }}
                      />
                      <span className="text-xs font-semibold text-[#F5F5F7]">
                        Scene {scenes.findIndex(s => s.id === selectedSceneId) + 1}
                      </span>
                      <span className="text-[10px] text-[#A1A1A8]">
                        {selectedScene.duration}s · {SCENE_STYLES.find(s => s.id === selectedScene.style)?.label}
                      </span>
                    </div>
                    <textarea
                      value={selectedScene.prompt}
                      onChange={e => updateScene(selectedScene.id, { prompt: e.target.value })}
                      placeholder="Describe this scene..."
                      rows={3}
                      className="w-full bg-[#0A0A0B] border border-[#1F1F23] rounded-lg px-3 py-2 text-[11px] text-[#F5F5F7] placeholder:text-[#A1A1A8]/25 resize-none focus:outline-none focus:border-[#7C5CFF]/30"
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Bottom Timeline Strip */}
          {view === 'storyboard' && (
            <div className="px-4 pb-3">
              <TimelineBar
                scenes={scenes}
                selectedId={selectedSceneId}
                onSelect={setSelectedSceneId}
              />
            </div>
          )}

          {/* Generate Bar */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-[#1F1F23] bg-[#131316]/80">
            <div className="flex items-center gap-3 text-[10px] text-[#A1A1A8]">
              <span>{scenes.filter(s => s.prompt.trim()).length} of {totalScenes} scenes written</span>
              <span className="text-[#1F1F23]">|</span>
              <span>{totalDuration}s total</span>
              {elements.length > 0 && (
                <>
                  <span className="text-[#1F1F23]">|</span>
                  <span>{elements.length} elements</span>
                </>
              )}
            </div>
            {isDemo ? (
              <button
                disabled
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1F1F23] text-[#A1A1A8]/50 text-[11px] font-medium cursor-not-allowed"
              >
                <Lock size={12} /> Sign up to generate
              </button>
            ) : (
              <button
                onClick={handleGenerate}
                disabled={generating || scenes.filter(s => s.prompt.trim()).length === 0}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#7C5CFF] text-white text-[11px] font-semibold hover:bg-[#7C5CFF]/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {generating ? (
                  <>
                    <Loader2 size={12} className="animate-spin" /> {genStatus}
                  </>
                ) : (
                  <>
                    <Zap size={12} /> Generate Commercial
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Right: Inspector Panel */}
        <AnimatePresence>
          {expandedInspector && selectedScene && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 240, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="border-l border-[#1F1F23] bg-[#131316] overflow-y-auto overflow-x-hidden flex-shrink-0"
            >
              <div className="w-[240px] p-3">
                <div className="flex items-center gap-1.5 mb-3">
                  <Settings2 size={10} className="text-[#A1A1A8]" />
                  <span className="text-[10px] font-bold text-[#A1A1A8] uppercase tracking-wider">
                    Inspector
                  </span>
                </div>
                <InspectorPanel
                  scene={selectedScene}
                  elements={elements}
                  onUpdate={patch => updateScene(selectedScene.id, patch)}
                  onToggleElement={() => {}}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
