import { useRef, useState, useEffect, Suspense, Component, type ReactNode } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { RoundedBox, Environment, Float, MeshTransmissionMaterial } from '@react-three/drei'
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

// CSS fallback for environments without WebGL
function CSSFallback() {
  return (
    <div className="absolute inset-0 flex items-center justify-center" style={{ perspective: '800px' }}>
      <div
        style={{
          transformStyle: 'preserve-3d',
          animation: 'visionSpin 6s ease-in-out infinite',
        }}
      >
        {/* Main visor */}
        <div
          style={{
            width: '220px',
            height: '90px',
            borderRadius: '45px',
            background: 'linear-gradient(135deg, #2a2a3e 0%, #1a1a2e 30%, #0d0d1a 70%, #1a1a2e 100%)',
            boxShadow: '0 0 60px rgba(124,58,237,0.2), inset 0 1px 0 rgba(255,255,255,0.08)',
            border: '1px solid rgba(124,58,237,0.25)',
            transform: 'translateZ(20px)',
            position: 'relative',
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: '4px',
              borderRadius: '41px',
              background: 'linear-gradient(145deg, rgba(124,58,237,0.15) 0%, rgba(26,143,214,0.1) 40%, rgba(23,197,176,0.08) 70%, rgba(124,58,237,0.12) 100%)',
            }}
          >
            <div
              style={{
                position: 'absolute',
                top: '6px',
                left: '15%',
                width: '70%',
                height: '40%',
                borderRadius: '50%',
                background: 'linear-gradient(180deg, rgba(255,255,255,0.1) 0%, transparent 100%)',
              }}
            />
          </div>
        </div>
        {/* Side bands */}
        <div style={{ position: 'absolute', width: '30px', height: '12px', top: '50%', left: '-14px', marginTop: '-6px', borderRadius: '6px', background: 'linear-gradient(90deg, #4a4a5e, #3a3a4e)', transform: 'rotateY(-25deg) translateZ(10px)' }} />
        <div style={{ position: 'absolute', width: '30px', height: '12px', top: '50%', right: '-14px', marginTop: '-6px', borderRadius: '6px', background: 'linear-gradient(270deg, #4a4a5e, #3a3a4e)', transform: 'rotateY(25deg) translateZ(10px)' }} />
        {/* Digital crown */}
        <div style={{ position: 'absolute', width: '8px', height: '8px', top: '30%', right: '-4px', borderRadius: '50%', background: 'radial-gradient(circle, #6a6a7e, #4a4a5e)', border: '1px solid rgba(255,255,255,0.1)', transform: 'translateZ(14px)' }} />
      </div>
      <style>{`
        @keyframes visionSpin {
          0%, 100% { transform: rotateY(-20deg) rotateX(5deg); }
          50% { transform: rotateY(20deg) rotateX(-3deg); }
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

function VisionProHeadset({ mouse }: { mouse: { x: number; y: number } }) {
  const groupRef = useRef<THREE.Group>(null!)

  useFrame((_, delta) => {
    if (!groupRef.current) return
    groupRef.current.rotation.y += delta * 0.3
    groupRef.current.rotation.x = THREE.MathUtils.lerp(
      groupRef.current.rotation.x,
      mouse.y * 0.15,
      0.05
    )
    groupRef.current.rotation.y += mouse.x * 0.002
  })

  return (
    <Float speed={1.5} rotationIntensity={0.1} floatIntensity={0.4} floatingRange={[-0.08, 0.08]}>
      <group ref={groupRef} position={[0, 0, 0]} scale={1.15}>
        {/* Main body — aluminum shell */}
        <RoundedBox args={[2.6, 1.05, 0.65]} radius={0.32} smoothness={8} position={[0, 0, 0]}>
          <meshStandardMaterial
            color="#8a8a92"
            metalness={0.85}
            roughness={0.18}
            envMapIntensity={1.2}
          />
        </RoundedBox>

        {/* Front glass visor */}
        <RoundedBox args={[2.5, 0.95, 0.12]} radius={0.28} smoothness={8} position={[0, 0, 0.32]}>
          <MeshTransmissionMaterial
            backside
            thickness={0.3}
            chromaticAberration={0.06}
            anisotropy={0.3}
            distortion={0.1}
            distortionScale={0.2}
            temporalDistortion={0.1}
            ior={1.5}
            color="#1a1025"
            attenuationColor="#2d1b4e"
            attenuationDistance={0.6}
            roughness={0.05}
            metalness={0.1}
            envMapIntensity={2}
            transmission={0.92}
          />
        </RoundedBox>

        {/* Glass visor outer rim */}
        <RoundedBox args={[2.55, 1.0, 0.06]} radius={0.3} smoothness={6} position={[0, 0, 0.35]}>
          <meshStandardMaterial
            color="#606068"
            metalness={0.9}
            roughness={0.15}
            envMapIntensity={1.5}
          />
        </RoundedBox>

        {/* Left lens dome */}
        <mesh position={[-0.52, 0, 0.33]}>
          <sphereGeometry args={[0.32, 32, 32, 0, Math.PI * 2, 0, Math.PI / 2]} />
          <meshPhysicalMaterial
            color="#0d0818"
            metalness={0.1}
            roughness={0.02}
            clearcoat={1}
            clearcoatRoughness={0.05}
            reflectivity={1}
            envMapIntensity={3}
            transparent
            opacity={0.7}
          />
        </mesh>

        {/* Right lens dome */}
        <mesh position={[0.52, 0, 0.33]}>
          <sphereGeometry args={[0.32, 32, 32, 0, Math.PI * 2, 0, Math.PI / 2]} />
          <meshPhysicalMaterial
            color="#0d0818"
            metalness={0.1}
            roughness={0.02}
            clearcoat={1}
            clearcoatRoughness={0.05}
            reflectivity={1}
            envMapIntensity={3}
            transparent
            opacity={0.7}
          />
        </mesh>

        {/* Top sensor bar */}
        <RoundedBox args={[1.4, 0.06, 0.15]} radius={0.03} smoothness={4} position={[0, 0.52, 0.15]}>
          <meshStandardMaterial color="#3a3a40" metalness={0.7} roughness={0.3} />
        </RoundedBox>

        {/* Front camera array — center */}
        <mesh position={[0, 0.42, 0.36]}>
          <cylinderGeometry args={[0.04, 0.04, 0.03, 16]} />
          <meshStandardMaterial color="#1a1a22" metalness={0.6} roughness={0.2} />
        </mesh>

        {/* Front camera — left */}
        <mesh position={[-0.18, 0.42, 0.36]}>
          <cylinderGeometry args={[0.025, 0.025, 0.03, 12]} />
          <meshStandardMaterial color="#1a1a22" metalness={0.6} roughness={0.2} />
        </mesh>

        {/* Front camera — right */}
        <mesh position={[0.18, 0.42, 0.36]}>
          <cylinderGeometry args={[0.025, 0.025, 0.03, 12]} />
          <meshStandardMaterial color="#1a1a22" metalness={0.6} roughness={0.2} />
        </mesh>

        {/* LiDAR dot */}
        <mesh position={[0, 0.42, 0.37]}>
          <sphereGeometry args={[0.012, 8, 8]} />
          <meshBasicMaterial color="#7c3aed" />
        </mesh>

        {/* Digital Crown — right side */}
        <mesh position={[1.32, 0.2, 0]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.07, 0.07, 0.06, 24]} />
          <meshStandardMaterial color="#aaaaae" metalness={0.9} roughness={0.1} />
        </mesh>

        {/* Crown ring detail */}
        <mesh position={[1.35, 0.2, 0]} rotation={[0, 0, Math.PI / 2]}>
          <torusGeometry args={[0.07, 0.008, 8, 24]} />
          <meshStandardMaterial color="#cccccc" metalness={0.95} roughness={0.05} />
        </mesh>

        {/* Top button — left side */}
        <mesh position={[-1.32, 0.3, 0]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.04, 0.04, 0.04, 16]} />
          <meshStandardMaterial color="#aaaaae" metalness={0.9} roughness={0.1} />
        </mesh>

        {/* Head band — left strap */}
        <RoundedBox args={[0.35, 0.45, 0.12]} radius={0.06} smoothness={4} position={[-1.35, -0.05, -0.1]}>
          <meshStandardMaterial color="#3a3a42" metalness={0.5} roughness={0.6} />
        </RoundedBox>

        {/* Head band — right strap */}
        <RoundedBox args={[0.35, 0.45, 0.12]} radius={0.06} smoothness={4} position={[1.35, -0.05, -0.1]}>
          <meshStandardMaterial color="#3a3a42" metalness={0.5} roughness={0.6} />
        </RoundedBox>

        {/* Solo knit band — flexible part */}
        {[-0.7, -0.35, 0, 0.35, 0.7].map((x, i) => (
          <RoundedBox
            key={i}
            args={[0.38, 0.28, 0.08]}
            radius={0.04}
            smoothness={3}
            position={[x, 0, -0.42]}
          >
            <meshStandardMaterial
              color="#2a2a30"
              metalness={0.1}
              roughness={0.85}
            />
          </RoundedBox>
        ))}

        {/* Inner cushion / light seal */}
        <RoundedBox args={[2.3, 0.85, 0.2]} radius={0.25} smoothness={6} position={[0, 0, -0.3]}>
          <meshStandardMaterial
            color="#1a1a1e"
            metalness={0.05}
            roughness={0.95}
          />
        </RoundedBox>

        {/* Speaker grille — left */}
        {[0, 1, 2].map(i => (
          <mesh key={`sl${i}`} position={[-1.1, -0.35 + i * 0.12, 0.1]}>
            <boxGeometry args={[0.15, 0.02, 0.02]} />
            <meshStandardMaterial color="#2a2a30" metalness={0.4} roughness={0.5} />
          </mesh>
        ))}

        {/* Speaker grille — right */}
        {[0, 1, 2].map(i => (
          <mesh key={`sr${i}`} position={[1.1, -0.35 + i * 0.12, 0.1]}>
            <boxGeometry args={[0.15, 0.02, 0.02]} />
            <meshStandardMaterial color="#2a2a30" metalness={0.4} roughness={0.5} />
          </mesh>
        ))}
      </group>
    </Float>
  )
}

function Lighting() {
  return (
    <>
      <ambientLight intensity={0.3} />
      <directionalLight position={[5, 5, 5]} intensity={1.2} color="#ffffff" />
      <directionalLight position={[-3, 3, -2]} intensity={0.4} color="#7c3aed" />
      <spotLight position={[0, 4, 2]} angle={0.4} penumbra={0.8} intensity={0.8} color="#a78bfa" />
      <pointLight position={[-4, -1, 3]} intensity={0.3} color="#1a8fd6" />
      <pointLight position={[4, -1, 3]} intensity={0.3} color="#17c5b0" />
    </>
  )
}

function GlowPlane() {
  return (
    <mesh position={[0, -1.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[6, 6]} />
      <meshBasicMaterial color="#7c3aed" transparent opacity={0.03} />
    </mesh>
  )
}

function Scene({ mouse }: { mouse: { x: number; y: number } }) {
  const { camera } = useThree()
  useEffect(() => {
    camera.position.set(0, 0.3, 4.5)
  }, [camera])

  return (
    <>
      <Lighting />
      <VisionProHeadset mouse={mouse} />
      <GlowPlane />
      <Environment preset="city" environmentIntensity={0.6} />
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
        background: 'radial-gradient(ellipse at 50% 50%, rgba(124,58,237,0.08) 0%, rgba(10,10,11,0) 70%)',
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
            <Canvas dpr={[1, 2]} gl={{ antialias: true, alpha: true }}>
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
