import { lazy, Suspense, useMemo, useState, useEffect } from 'react'

interface SceneRendererProps {
  sceneId: string
  primaryColor: string
  accentColor: string
}

/* ── Lazy-loaded scene components ─────────────────────────────── */
const scenes: Record<string, React.LazyExoticComponent<React.ComponentType<{ primaryColor: string; accentColor: string }>>> = {
  '3d_aurora':          lazy(() => import('./scenes/AuroraScene')),
  '3d_neon_grid':       lazy(() => import('./scenes/NeonGridScene')),
  '3d_particles':       lazy(() => import('./scenes/ParticlesScene')),
  '3d_waves':           lazy(() => import('./scenes/WavesScene')),
  '3d_smoke':           lazy(() => import('./scenes/SmokeScene')),
  '3d_glass_morphism':  lazy(() => import('./scenes/GlassMorphismScene')),
  '3d_geometric':       lazy(() => import('./scenes/GeometricScene')),
  '3d_gradient_mesh':   lazy(() => import('./scenes/GradientMeshScene')),
  '3d_bokeh':           lazy(() => import('./scenes/BokehScene')),
  '3d_parallax_depth':  lazy(() => import('./scenes/ParallaxDepthScene')),
  '3d_floating_orbs':   lazy(() => import('./scenes/FloatingOrbsScene')),
  '3d_crystal':         lazy(() => import('./scenes/CrystalScene')),
  '3d_fog_dark':        lazy(() => import('./scenes/FogDarkScene')),
  '3d_starfield':       lazy(() => import('./scenes/StarfieldScene')),
  '3d_lava_lamp':       lazy(() => import('./scenes/LavaLampScene')),
  '3d_ripple_water':    lazy(() => import('./scenes/RippleWaterScene')),
  '3d_morphing_blob':   lazy(() => import('./scenes/MorphingBlobScene')),
  '3d_liquid_metal':    lazy(() => import('./scenes/LiquidMetalScene')),
  '3d_holographic':     lazy(() => import('./scenes/HolographicScene')),
  '3d_minimal_noise':   lazy(() => import('./scenes/MinimalNoiseScene')),
}

const DEFAULT_SCENE_ID = '3d_particles'

type PerfTier = 'high' | 'low' | 'none'

function detectPerformanceTier(): PerfTier {
  if (typeof window === 'undefined') return 'none'

  const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
  const cores = navigator.hardwareConcurrency || 2
  const memory = (navigator as any).deviceMemory as number | undefined
  const prefersReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

  if (prefersReduced) return 'none'

  try {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl')
    if (!gl) return 'none'
    const dbg = gl.getExtension('WEBGL_debug_renderer_info')
    if (dbg) {
      const renderer = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)?.toLowerCase() || ''
      if (renderer.includes('swiftshader') || renderer.includes('llvmpipe') || renderer.includes('software'))
        return 'none'
    }
    canvas.remove()
  } catch {
    return 'none'
  }

  if (isMobile && (cores <= 4 || (memory !== undefined && memory <= 3)))
    return 'low'

  if (cores <= 2 || (memory !== undefined && memory <= 2))
    return 'low'

  return 'high'
}

let cachedTier: PerfTier | null = null
function getPerformanceTier(): PerfTier {
  if (cachedTier === null) cachedTier = detectPerformanceTier()
  return cachedTier
}

function StaticBackground({ primaryColor, accentColor }: { primaryColor: string; accentColor: string }) {
  return (
    <div className="absolute inset-0 overflow-hidden">
      <div
        className="absolute inset-0"
        style={{ background: `radial-gradient(ellipse at 50% 30%, ${accentColor}18, ${primaryColor})` }}
      />
      <div
        className="absolute w-[600px] h-[600px] rounded-full blur-[120px] opacity-[0.07] top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2"
        style={{ background: accentColor }}
      />
      <div
        className="absolute w-[300px] h-[300px] rounded-full blur-[80px] opacity-[0.04] bottom-1/4 right-1/4"
        style={{ background: accentColor }}
      />
    </div>
  )
}

export default function SceneRenderer({ sceneId, primaryColor, accentColor }: SceneRendererProps) {
  const [tier, setTier] = useState<PerfTier>('high')

  useEffect(() => {
    setTier(getPerformanceTier())
  }, [])

  const SceneComponent = useMemo(
    () => scenes[sceneId] || scenes[DEFAULT_SCENE_ID],
    [sceneId],
  )

  if (tier === 'none') {
    return <StaticBackground primaryColor={primaryColor} accentColor={accentColor} />
  }

  return (
    <Suspense
      fallback={
        <div
          className="absolute inset-0"
          style={{ background: `radial-gradient(ellipse at 50% 30%, ${accentColor}15, ${primaryColor})` }}
        />
      }
    >
      <SceneComponent primaryColor={primaryColor} accentColor={accentColor} />
    </Suspense>
  )
}

export { getPerformanceTier, type PerfTier }
