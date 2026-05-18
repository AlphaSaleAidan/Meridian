import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function Orb({ position, scale, color, speed, metallic }: {
  position: [number, number, number]; scale: number; color: string; speed: number; metallic?: boolean
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.y = clock.getElapsedTime() * speed * 0.2
  })
  return (
    <Float speed={speed} rotationIntensity={0.2} floatIntensity={0.8}>
      <mesh ref={ref} position={position} scale={scale}>
        <sphereGeometry args={[1, 64, 64]} />
        {metallic ? (
          <meshPhysicalMaterial
            color={color} metalness={0.95} roughness={0.05} envMapIntensity={2.5}
            iridescence={0.8} iridescenceIOR={1.3}
            iridescenceThicknessRange={[100, 400]}
            clearcoat={1} clearcoatRoughness={0.05}
          />
        ) : (
          <MeshTransmissionMaterial
            backside thickness={0.4} chromaticAberration={0.6}
            color={color} roughness={0.0} transmission={0.97} ior={1.8}
            distortion={0.3} distortionScale={0.5} temporalDistortion={0.15}
          />
        )}
      </mesh>
    </Float>
  )
}

function VortexParticles({ count, color, radius }: { count: number; color: string; radius: number }) {
  const ref = useRef<THREE.Points>(null)
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const t = (i / count) * Math.PI * 12
      const r = radius * (0.3 + (i / count) * 0.7)
      const scatter = (Math.random() - 0.5) * 0.5
      pos[i * 3] = Math.cos(t) * r + scatter
      pos[i * 3 + 1] = (Math.random() - 0.5) * 3
      pos[i * 3 + 2] = Math.sin(t) * r + scatter
    }
    return pos
  }, [count, radius])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.03
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={count} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial color={color} size={0.02} sizeAttenuation transparent opacity={0.5} blending={THREE.AdditiveBlending} />
    </points>
  )
}

function OrbField({ primaryColor, accentColor }: SceneProps) {
  const orbs = useMemo(() => [
    { pos: [0, 0.3, 0] as [number, number, number], scale: 1.0, color: accentColor, speed: 1.0, metallic: false },
    { pos: [-2.8, 0.8, -2] as [number, number, number], scale: 0.6, color: primaryColor, speed: 1.5, metallic: true },
    { pos: [2.5, -0.5, -1] as [number, number, number], scale: 0.45, color: accentColor, speed: 1.8, metallic: false },
    { pos: [-1.5, -1.3, 0.5] as [number, number, number], scale: 0.35, color: primaryColor, speed: 2.0, metallic: true },
    { pos: [1.8, 1.6, -2.5] as [number, number, number], scale: 0.5, color: accentColor, speed: 1.3, metallic: false },
    { pos: [3, -1, -1.5] as [number, number, number], scale: 0.25, color: primaryColor, speed: 2.2, metallic: true },
    { pos: [-0.8, 2, -1] as [number, number, number], scale: 0.3, color: accentColor, speed: 1.7, metallic: false },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#030306']} />
      <fog attach="fog" args={['#030306', 3, 14]} />
      <ambientLight intensity={0.12} />
      <pointLight position={[4, 3, 2]} intensity={3} color={accentColor} distance={15} />
      <pointLight position={[-3, -2, 3]} intensity={2} color={primaryColor} distance={12} />
      <directionalLight position={[0, 5, 5]} intensity={0.5} color="#ffffff" />
      <Environment preset="city" />
      {orbs.map((o, i) => (
        <Orb key={i} position={o.pos} scale={o.scale} color={o.color} speed={o.speed} metallic={o.metallic} />
      ))}
      <VortexParticles count={2000} color={accentColor} radius={5} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.12} luminanceSmoothing={0.9} intensity={1.4} />
      </EffectComposer>
    </>
  )
}

export default function FloatingOrbsScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 6], fov: 45 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.5 }}
    >
      <OrbField primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
