import { useRef, useState, useEffect, useMemo, Suspense, Component, type ReactNode } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Environment, Float } from '@react-three/drei'
import * as THREE from 'three'
import { motion } from 'framer-motion'

function hasWebGL(): boolean {
  try {
    const c = document.createElement('canvas')
    return !!(c.getContext('webgl2') || c.getContext('webgl') || c.getContext('experimental-webgl'))
  } catch {
    return false
  }
}

function CSSFallback() {
  return (
    <div className="absolute inset-0 flex items-center justify-center" style={{ perspective: '800px' }}>
      <div
        style={{
          transformStyle: 'preserve-3d',
          animation: 'visionSpin 6s ease-in-out infinite',
        }}
      >
        <div
          style={{
            width: '240px',
            height: '100px',
            borderRadius: '50px',
            background: 'linear-gradient(135deg, #c0c0c8 0%, #a0a0a8 5%, #1c1c2e 8%, #2d2d3d 50%, #1c1c2e 92%, #a0a0a8 95%, #c0c0c8 100%)',
            boxShadow: '0 0 60px rgba(124,58,237,0.15), 0 8px 32px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.15)',
            position: 'relative',
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: '3px 12px',
              borderRadius: '47px',
              background: 'linear-gradient(180deg, rgba(255,255,255,0.06) 0%, transparent 50%, rgba(255,255,255,0.03) 100%)',
            }}
          />
        </div>
      </div>
      <style>{`
        @keyframes visionSpin {
          0%, 100% { transform: rotateY(-15deg) rotateX(3deg); }
          50% { transform: rotateY(15deg) rotateX(-2deg); }
        }
      `}</style>
    </div>
  )
}

class WebGLErrorBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  render() {
    return this.state.hasError ? this.props.fallback : this.props.children
  }
}

function VisorGlass() {
  const glassShape = useMemo(() => {
    const shape = new THREE.Shape()
    const w = 2.4
    const h = 0.95
    const r = 0.42
    shape.moveTo(-w / 2 + r, -h / 2)
    shape.lineTo(w / 2 - r, -h / 2)
    shape.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r)
    shape.lineTo(w / 2, h / 2 - r)
    shape.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2)
    shape.lineTo(-w / 2 + r, h / 2)
    shape.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r)
    shape.lineTo(-w / 2, -h / 2 + r)
    shape.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2)
    return shape
  }, [])

  const glassGeo = useMemo(() => {
    const geo = new THREE.ExtrudeGeometry(glassShape, {
      depth: 0.08,
      bevelEnabled: true,
      bevelThickness: 0.06,
      bevelSize: 0.04,
      bevelSegments: 8,
      curveSegments: 24,
    })
    geo.center()
    return geo
  }, [glassShape])

  return (
    <mesh geometry={glassGeo} position={[0, 0, 0.22]}>
      <meshPhysicalMaterial
        color="#22223a"
        metalness={0.2}
        roughness={0.04}
        transmission={0.08}
        thickness={0.5}
        ior={1.52}
        envMapIntensity={3.0}
        clearcoat={1}
        clearcoatRoughness={0.01}
        reflectivity={1}
        sheen={0.3}
        sheenColor={new THREE.Color('#3d3d5c')}
        transparent
      />
    </mesh>
  )
}

function AluminumFrame() {
  const frameShape = useMemo(() => {
    const shape = new THREE.Shape()
    const w = 2.55
    const h = 1.05
    const r = 0.46
    shape.moveTo(-w / 2 + r, -h / 2)
    shape.lineTo(w / 2 - r, -h / 2)
    shape.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r)
    shape.lineTo(w / 2, h / 2 - r)
    shape.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2)
    shape.lineTo(-w / 2 + r, h / 2)
    shape.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r)
    shape.lineTo(-w / 2, -h / 2 + r)
    shape.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2)
    return shape
  }, [])

  const frameGeo = useMemo(() => {
    const geo = new THREE.ExtrudeGeometry(frameShape, {
      depth: 0.4,
      bevelEnabled: true,
      bevelThickness: 0.04,
      bevelSize: 0.03,
      bevelSegments: 6,
      curveSegments: 24,
    })
    geo.center()
    return geo
  }, [frameShape])

  return (
    <mesh geometry={frameGeo} position={[0, 0, 0]}>
      <meshStandardMaterial
        color="#d4d4dc"
        metalness={0.9}
        roughness={0.18}
        envMapIntensity={1.6}
      />
    </mesh>
  )
}

function SensorDot({ position, size = 0.025 }: { position: [number, number, number]; size?: number }) {
  return (
    <mesh position={position}>
      <circleGeometry args={[size, 16]} />
      <meshStandardMaterial color="#0a0a14" metalness={0.3} roughness={0.4} />
    </mesh>
  )
}

function VisionProHeadset({ mouse }: { mouse: { x: number; y: number } }) {
  const groupRef = useRef<THREE.Group>(null!)

  useFrame((_, delta) => {
    if (!groupRef.current) return
    groupRef.current.rotation.y += delta * 0.25
    groupRef.current.rotation.x = THREE.MathUtils.lerp(
      groupRef.current.rotation.x,
      mouse.y * 0.12,
      0.04
    )
    groupRef.current.rotation.y += mouse.x * 0.0015
  })

  return (
    <Float speed={1.2} rotationIntensity={0.08} floatIntensity={0.3} floatingRange={[-0.06, 0.06]}>
      <group ref={groupRef} position={[0, 0, 0]} scale={1.1}>

        {/* Aluminum frame/body — the structural shell */}
        <AluminumFrame />

        {/* Front glass visor — the signature dark curved glass */}
        <VisorGlass />

        {/* Glass surface highlight — reflection strip across top third */}
        <mesh position={[0, 0.15, 0.31]}>
          <planeGeometry args={[1.6, 0.12]} />
          <meshBasicMaterial color="#ffffff" transparent opacity={0.06} />
        </mesh>
        {/* Secondary highlight — subtle lower reflection */}
        <mesh position={[0, -0.08, 0.31]}>
          <planeGeometry args={[1.2, 0.06]} />
          <meshBasicMaterial color="#ffffff" transparent opacity={0.03} />
        </mesh>

        {/* Polished aluminum bezel lip — visible edge where glass meets frame */}
        {[
          { pos: [0, 0.52, 0.18] as [number, number, number], size: [2.35, 0.025, 0.14] as [number, number, number] },
          { pos: [0, -0.52, 0.18] as [number, number, number], size: [2.35, 0.025, 0.14] as [number, number, number] },
          { pos: [-1.26, 0, 0.18] as [number, number, number], size: [0.025, 0.94, 0.14] as [number, number, number] },
          { pos: [1.26, 0, 0.18] as [number, number, number], size: [0.025, 0.94, 0.14] as [number, number, number] },
        ].map(({ pos, size }, i) => (
          <mesh key={`bezel-${i}`} position={pos}>
            <boxGeometry args={size} />
            <meshStandardMaterial color="#e0e0e8" metalness={0.95} roughness={0.06} envMapIntensity={2.0} />
          </mesh>
        ))}

        {/* Sensor cameras — subtle dark dots behind glass */}
        {/* Top center — LiDAR */}
        <SensorDot position={[0, 0.35, 0.28]} size={0.03} />
        {/* RGB cameras flanking nose bridge */}
        <SensorDot position={[-0.15, 0.32, 0.28]} size={0.022} />
        <SensorDot position={[0.15, 0.32, 0.28]} size={0.022} />
        {/* Tracking cameras — upper corners */}
        <SensorDot position={[-0.65, 0.3, 0.26]} size={0.018} />
        <SensorDot position={[0.65, 0.3, 0.26]} size={0.018} />
        {/* Side tracking cameras */}
        <SensorDot position={[-0.9, 0.15, 0.24]} size={0.016} />
        <SensorDot position={[0.9, 0.15, 0.24]} size={0.016} />
        {/* Lower tracking cameras */}
        <SensorDot position={[-0.5, -0.3, 0.26]} size={0.016} />
        <SensorDot position={[0.5, -0.3, 0.26]} size={0.016} />

        {/* Digital Crown — top right, polished aluminum knurled cylinder */}
        <group position={[0.95, 0.48, 0.05]}>
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.055, 0.055, 0.045, 32]} />
            <meshStandardMaterial color="#d8d8de" metalness={0.92} roughness={0.08} envMapIntensity={1.8} />
          </mesh>
          {/* Crown ring/knurl detail */}
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[0.055, 0.005, 8, 32]} />
            <meshStandardMaterial color="#e0e0e6" metalness={0.95} roughness={0.05} />
          </mesh>
          {/* Crown cap */}
          <mesh position={[0, 0.024, 0]} rotation={[Math.PI / 2, 0, 0]}>
            <circleGeometry args={[0.053, 32]} />
            <meshStandardMaterial color="#c8c8d0" metalness={0.9} roughness={0.12} />
          </mesh>
        </group>

        {/* Top button — top left, flush aluminum circle */}
        <group position={[-0.85, 0.48, 0.05]}>
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.04, 0.04, 0.02, 24]} />
            <meshStandardMaterial color="#d0d0d8" metalness={0.9} roughness={0.1} envMapIntensity={1.6} />
          </mesh>
        </group>

        {/* Temple arms — polished aluminum connecting to headband */}
        {/* Left arm */}
        <mesh position={[-1.28, 0, -0.08]} rotation={[0, 0.15, 0]}>
          <boxGeometry args={[0.12, 0.4, 0.22]} />
          <meshStandardMaterial color="#b8b8c0" metalness={0.85} roughness={0.2} />
        </mesh>
        {/* Right arm */}
        <mesh position={[1.28, 0, -0.08]} rotation={[0, -0.15, 0]}>
          <boxGeometry args={[0.12, 0.4, 0.22]} />
          <meshStandardMaterial color="#b8b8c0" metalness={0.85} roughness={0.2} />
        </mesh>

        {/* Audio pods — integrated into temple arms */}
        {/* Left pod */}
        <mesh position={[-1.35, -0.08, -0.12]} rotation={[0.1, 0.2, 0]}>
          <capsuleGeometry args={[0.06, 0.16, 8, 16]} />
          <meshStandardMaterial color="#c0c0c8" metalness={0.88} roughness={0.18} />
        </mesh>
        {/* Right pod */}
        <mesh position={[1.35, -0.08, -0.12]} rotation={[0.1, -0.2, 0]}>
          <capsuleGeometry args={[0.06, 0.16, 8, 16]} />
          <meshStandardMaterial color="#c0c0c8" metalness={0.88} roughness={0.18} />
        </mesh>

        {/* Speaker mesh grilles — tiny perforated pattern on audio pods */}
        {[-1, 1].map(side => (
          <group key={`spk-${side}`}>
            {[0, 1, 2, 3, 4].map(i => (
              <mesh key={i} position={[side * 1.38, -0.14 + i * 0.035, -0.06]} rotation={[0, side * 0.2, 0]}>
                <boxGeometry args={[0.04, 0.008, 0.008]} />
                <meshStandardMaterial color="#888890" metalness={0.5} roughness={0.4} />
              </mesh>
            ))}
          </group>
        ))}

        {/* Light Seal — soft gray fabric cushion on inner face */}
        <mesh position={[0, 0, -0.22]}>
          <planeGeometry args={[2.2, 0.85]} />
          <meshStandardMaterial
            color="#8C8C8C"
            metalness={0}
            roughness={0.92}
            side={THREE.BackSide}
          />
        </mesh>

        {/* Solo Knit Band — woven fabric headband */}
        {/* Curved band segments going around the back */}
        {[-0.8, -0.4, 0, 0.4, 0.8].map((x, i) => (
          <mesh
            key={`band-${i}`}
            position={[x, 0, -0.38 - Math.abs(x) * 0.06]}
            scale={[1, 1, 0.6]}
          >
            <capsuleGeometry args={[0.13, 0.22, 4, 12]} />
            <meshStandardMaterial
              color="#D4D4D4"
              metalness={0}
              roughness={0.88}
            />
          </mesh>
        ))}

        {/* Band inner accent — orange interior detail */}
        {[-0.4, 0, 0.4].map((x, i) => (
          <mesh
            key={`accent-${i}`}
            position={[x, 0, -0.44 - Math.abs(x) * 0.04]}
            scale={[1, 0.7, 0.3]}
          >
            <capsuleGeometry args={[0.1, 0.18, 4, 8]} />
            <meshStandardMaterial color="#E8732A" metalness={0} roughness={0.85} />
          </mesh>
        ))}

        {/* Nose bridge indent — subtle dark area at center bottom */}
        <mesh position={[0, -0.38, 0.22]}>
          <sphereGeometry args={[0.12, 16, 16]} />
          <meshStandardMaterial color="#1a1a24" metalness={0.2} roughness={0.3} />
        </mesh>
      </group>
    </Float>
  )
}

function Lighting() {
  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 5, 5]} intensity={1.2} color="#ffffff" />
      <directionalLight position={[-3, 4, -2]} intensity={0.4} color="#c0c0d0" />
      <spotLight position={[0, 6, 4]} angle={0.3} penumbra={0.7} intensity={0.9} color="#f0f0ff" />
      <spotLight position={[2, 2, 5]} angle={0.5} penumbra={0.9} intensity={0.4} color="#ffffff" />
      <pointLight position={[-4, -1, 4]} intensity={0.25} color="#7c3aed" />
      <pointLight position={[4, -1, 4]} intensity={0.25} color="#00d4aa" />
    </>
  )
}

function Scene({ mouse }: { mouse: { x: number; y: number } }) {
  const { camera } = useThree()
  useEffect(() => {
    camera.position.set(0, 0.2, 4.2)
  }, [camera])

  return (
    <>
      <Lighting />
      <VisionProHeadset mouse={mouse} />
      <mesh position={[0, -1.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[6, 6]} />
        <meshBasicMaterial color="#7c3aed" transparent opacity={0.02} />
      </mesh>
      <Environment preset="city" environmentIntensity={0.7} />
    </>
  )
}

export default function VisionProHero() {
  const [mouse, setMouse] = useState({ x: 0, y: 0 })
  const [webgl, setWebgl] = useState(true)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setWebgl(hasWebGL())
  }, [])

  useEffect(() => {
    function handleMove(e: MouseEvent) {
      if (!containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const x = ((e.clientX - rect.left) / rect.width - 0.5) * 2
      const y = ((e.clientY - rect.top) / rect.height - 0.5) * -2
      setMouse({ x, y })
    }
    window.addEventListener('mousemove', handleMove)
    return () => window.removeEventListener('mousemove', handleMove)
  }, [])

  return (
    <motion.div
      ref={containerRef}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
      className="relative w-full h-[340px] sm:h-[400px]"
      style={{
        background: 'radial-gradient(ellipse at 50% 50%, rgba(124,58,237,0.06) 0%, rgba(10,10,11,0) 70%)',
      }}
    >
      {webgl ? (
        <WebGLErrorBoundary fallback={<CSSFallback />}>
          <Suspense fallback={
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-10 h-10 rounded-xl bg-[#7c3aed]/10 border border-[#7c3aed]/20 flex items-center justify-center animate-pulse">
                <span className="text-[#7c3aed] font-bold text-sm">VP</span>
              </div>
            </div>
          }>
            <Canvas
              dpr={[1, 2]}
              gl={{ antialias: true, alpha: true, powerPreference: 'default', failIfMajorPerformanceCaveat: false }}
              onCreated={({ gl }) => { gl.setClearColor(0x000000, 0) }}
            >
              <Scene mouse={mouse} />
            </Canvas>
          </Suspense>
        </WebGLErrorBoundary>
      ) : (
        <CSSFallback />
      )}
    </motion.div>
  )
}
