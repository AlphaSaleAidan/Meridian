import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function Crystal({ position, rotation, scale, color, speed }: {
  position: [number, number, number]; rotation: [number, number, number]
  scale: number; color: string; speed: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime() * speed
    ref.current.rotation.x = rotation[0] + t * 0.3
    ref.current.rotation.y = rotation[1] + t * 0.2
  })
  return (
    <Float speed={speed * 2} rotationIntensity={0.3} floatIntensity={0.5}>
      <mesh ref={ref} position={position} scale={scale}>
        <icosahedronGeometry args={[1, 0]} />
        <MeshTransmissionMaterial
          backside thickness={0.5} chromaticAberration={0.4}
          anisotropy={0.3} distortion={0.2} distortionScale={0.2}
          temporalDistortion={0.1} color={color} roughness={0.02}
          transmission={0.95} ior={1.8}
        />
      </mesh>
    </Float>
  )
}

function PrismaticShard({ position, scale, color, speed }: {
  position: [number, number, number]; scale: number; color: string; speed: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.x = clock.getElapsedTime() * speed * 0.4
    ref.current.rotation.z = clock.getElapsedTime() * speed * 0.3
  })
  return (
    <Float speed={speed} rotationIntensity={0.2} floatIntensity={0.4}>
      <mesh ref={ref} position={position} scale={scale}>
        <coneGeometry args={[0.5, 2, 4]} />
        <meshPhysicalMaterial
          color={color} metalness={0.05} roughness={0.02}
          transmission={0.85} thickness={0.4} ior={2.0}
          iridescence={1} iridescenceIOR={1.5}
          iridescenceThicknessRange={[100, 600]}
          clearcoat={1} clearcoatRoughness={0}
        />
      </mesh>
    </Float>
  )
}

function CrystalDust({ count, color, spread }: { count: number; color: string; spread: number }) {
  const ref = useRef<THREE.Points>(null)
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * spread
      pos[i * 3 + 1] = (Math.random() - 0.5) * spread
      pos[i * 3 + 2] = (Math.random() - 0.5) * spread
    }
    return pos
  }, [count, spread])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.02
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={count} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial color={color} size={0.02} sizeAttenuation transparent opacity={0.6} blending={THREE.AdditiveBlending} />
    </points>
  )
}

function CrystalField({ primaryColor, accentColor }: SceneProps) {
  const crystals = useMemo(() => [
    { pos: [0, 0, 0] as [number, number, number], rot: [0, 0, 0] as [number, number, number], scale: 1.2, color: accentColor, speed: 0.5 },
    { pos: [-2.5, 1, -1] as [number, number, number], rot: [0.5, 0.3, 0] as [number, number, number], scale: 0.7, color: primaryColor, speed: 0.7 },
    { pos: [2.2, -0.8, -0.5] as [number, number, number], rot: [0.2, 0.8, 0.1] as [number, number, number], scale: 0.5, color: accentColor, speed: 0.9 },
    { pos: [-1.5, -1.2, 0.5] as [number, number, number], rot: [0.7, 0.1, 0.4] as [number, number, number], scale: 0.4, color: primaryColor, speed: 0.6 },
    { pos: [1.8, 1.5, -1.5] as [number, number, number], rot: [0.3, 0.6, 0.2] as [number, number, number], scale: 0.6, color: accentColor, speed: 0.8 },
    { pos: [0.5, -1.8, 1] as [number, number, number], rot: [0.9, 0.2, 0.5] as [number, number, number], scale: 0.35, color: primaryColor, speed: 1.0 },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#050508']} />
      <fog attach="fog" args={['#050508', 4, 14]} />
      <ambientLight intensity={0.15} />
      <pointLight position={[3, 3, 3]} intensity={2.5} color={accentColor} />
      <pointLight position={[-3, -2, 2]} intensity={1.5} color={primaryColor} />
      <spotLight position={[0, 5, 0]} intensity={1.5} angle={0.5} penumbra={1} color="#ffffff" />
      <Environment preset="city" />
      {crystals.map((c, i) => (
        <Crystal key={i} position={c.pos} rotation={c.rot} scale={c.scale} color={c.color} speed={c.speed} />
      ))}
      <PrismaticShard position={[-1, 2, -1]} scale={0.3} color={accentColor} speed={0.6} />
      <PrismaticShard position={[2.5, -1, -2]} scale={0.25} color={primaryColor} speed={0.8} />
      <CrystalDust count={800} color={accentColor} spread={10} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.15} luminanceSmoothing={0.9} intensity={1.8} />
      </EffectComposer>
    </>
  )
}

export default function CrystalScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 5], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.4 }}
    >
      <CrystalField primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
