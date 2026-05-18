import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function MistLayer({ position, scale, color, speed, opacity }: {
  position: [number, number, number]; scale: [number, number, number]
  color: string; speed: number; opacity: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime() * speed
    ref.current.position.x = position[0] + Math.sin(t * 0.3) * 1.5
    ref.current.position.y = position[1] + Math.cos(t * 0.2) * 0.5
    ref.current.scale.x = scale[0] + Math.sin(t * 0.15) * 0.3
    ref.current.scale.y = scale[1] + Math.cos(t * 0.12) * 0.2
  })
  return (
    <mesh ref={ref} position={position}>
      <sphereGeometry args={[1, 32, 32]} />
      <meshBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} blending={THREE.AdditiveBlending} />
    </mesh>
  )
}

function EmberOrb({ position, scale, color, speed }: {
  position: [number, number, number]; scale: number; color: string; speed: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.y = clock.getElapsedTime() * speed * 0.2
  })
  return (
    <Float speed={speed} rotationIntensity={0.1} floatIntensity={0.6}>
      <mesh ref={ref} position={position} scale={scale}>
        <sphereGeometry args={[1, 48, 48]} />
        <MeshTransmissionMaterial
          backside thickness={0.5} chromaticAberration={0.15}
          color={color} roughness={0.1} transmission={0.92} ior={1.4}
          distortion={0.2} distortionScale={0.3} temporalDistortion={0.1}
        />
      </mesh>
    </Float>
  )
}

function GlowPoint({ position, color, scale }: {
  position: [number, number, number]; color: string; scale: number
}) {
  return (
    <Float speed={2} floatIntensity={1}>
      <mesh position={position} scale={scale}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
    </Float>
  )
}

function SmokeContent({ primaryColor, accentColor }: SceneProps) {
  const mists = useMemo(() => [
    { pos: [-2, -1, -3] as [number, number, number], scale: [3, 2, 2] as [number, number, number], color: accentColor, speed: 0.4, opacity: 0.04 },
    { pos: [2, 0, -4] as [number, number, number], scale: [3.5, 2.5, 2] as [number, number, number], color: primaryColor, speed: 0.3, opacity: 0.035 },
    { pos: [0, 1.5, -5] as [number, number, number], scale: [4, 2, 2.5] as [number, number, number], color: accentColor, speed: 0.5, opacity: 0.03 },
    { pos: [-1, -2, -3.5] as [number, number, number], scale: [2.5, 1.8, 2] as [number, number, number], color: primaryColor, speed: 0.35, opacity: 0.04 },
  ], [primaryColor, accentColor])

  const orbs = useMemo(() => [
    { pos: [0, 0, 0] as [number, number, number], scale: 0.6, color: accentColor, speed: 0.7 },
    { pos: [-2, 1, -2] as [number, number, number], scale: 0.4, color: primaryColor, speed: 0.9 },
    { pos: [2.5, -0.5, -1.5] as [number, number, number], scale: 0.35, color: accentColor, speed: 0.8 },
    { pos: [-1, -1.5, -1] as [number, number, number], scale: 0.3, color: primaryColor, speed: 1.0 },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#020204']} />
      <fog attach="fog" args={['#020204', 2, 12]} />
      <ambientLight intensity={0.05} />
      <pointLight position={[3, 3, 3]} intensity={1.5} color={accentColor} distance={12} />
      <pointLight position={[-3, -2, 2]} intensity={1} color={primaryColor} distance={10} />
      {mists.map((m, i) => (
        <MistLayer key={`m${i}`} position={m.pos} scale={m.scale} color={m.color} speed={m.speed} opacity={m.opacity} />
      ))}
      {orbs.map((o, i) => (
        <EmberOrb key={`o${i}`} position={o.pos} scale={o.scale} color={o.color} speed={o.speed} />
      ))}
      <GlowPoint position={[2, 1.5, -2]} color={accentColor} scale={0.06} />
      <GlowPoint position={[-1.5, -1, -1.5]} color={primaryColor} scale={0.05} />
      <GlowPoint position={[0, 2, -3]} color={accentColor} scale={0.04} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.1} luminanceSmoothing={0.95} intensity={1.8} />
      </EffectComposer>
    </>
  )
}

export default function SmokeScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 5], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.6 }}
    >
      <SmokeContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
