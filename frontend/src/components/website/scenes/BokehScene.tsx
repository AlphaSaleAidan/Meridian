import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function GlassOrb({ position, scale, color, speed, transmission }: {
  position: [number, number, number]; scale: number; color: string; speed: number; transmission: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.y = clock.getElapsedTime() * speed * 0.15
  })
  return (
    <Float speed={speed} rotationIntensity={0.1} floatIntensity={0.6}>
      <mesh ref={ref} position={position} scale={scale}>
        <sphereGeometry args={[1, 48, 48]} />
        <MeshTransmissionMaterial
          backside thickness={0.3} chromaticAberration={0.4}
          color={color} roughness={0.0} transmission={transmission} ior={1.6}
          distortion={0.15} distortionScale={0.3} temporalDistortion={0.1}
        />
      </mesh>
    </Float>
  )
}

function GlowDot({ position, color, scale }: {
  position: [number, number, number]; color: string; scale: number
}) {
  return (
    <Float speed={2.5} floatIntensity={1.2}>
      <mesh position={position} scale={scale}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
    </Float>
  )
}

function BokehContent({ primaryColor, accentColor }: SceneProps) {
  const orbs = useMemo(() => [
    { pos: [0, 0, 0] as [number, number, number], scale: 0.9, color: accentColor, speed: 0.8, transmission: 0.97 },
    { pos: [-2.5, 1, -2] as [number, number, number], scale: 0.55, color: primaryColor, speed: 1.2, transmission: 0.95 },
    { pos: [2, -0.8, -1.5] as [number, number, number], scale: 0.4, color: accentColor, speed: 1.5, transmission: 0.96 },
    { pos: [-1.2, -1.5, -0.5] as [number, number, number], scale: 0.35, color: primaryColor, speed: 1.0, transmission: 0.94 },
    { pos: [1.8, 1.6, -2.5] as [number, number, number], scale: 0.5, color: accentColor, speed: 0.9, transmission: 0.97 },
    { pos: [3, 0, -1] as [number, number, number], scale: 0.25, color: primaryColor, speed: 1.8, transmission: 0.95 },
    { pos: [-0.5, 2, -1.5] as [number, number, number], scale: 0.3, color: accentColor, speed: 1.3, transmission: 0.96 },
    { pos: [-2, -0.5, 0.5] as [number, number, number], scale: 0.2, color: primaryColor, speed: 2.0, transmission: 0.93 },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#030306']} />
      <fog attach="fog" args={['#030306', 4, 16]} />
      <ambientLight intensity={0.08} />
      <pointLight position={[4, 3, 3]} intensity={2.5} color={accentColor} distance={15} />
      <pointLight position={[-3, -2, 4]} intensity={1.8} color={primaryColor} distance={12} />
      <spotLight position={[0, 5, 2]} intensity={1} angle={0.4} penumbra={1} color="#ffffff" />
      {orbs.map((o, i) => (
        <GlassOrb key={i} position={o.pos} scale={o.scale} color={o.color} speed={o.speed} transmission={o.transmission} />
      ))}
      <GlowDot position={[3, 2, -3]} color={accentColor} scale={0.08} />
      <GlowDot position={[-2.5, -1.5, -2]} color={primaryColor} scale={0.06} />
      <GlowDot position={[1, -2, -4]} color={accentColor} scale={0.05} />
      <GlowDot position={[-1, 2.5, -3]} color={primaryColor} scale={0.07} />
      <GlowDot position={[2, 0.5, -5]} color={accentColor} scale={0.04} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.15} luminanceSmoothing={0.9} intensity={1.3} />
      </EffectComposer>
    </>
  )
}

export default function BokehScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 6], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.5 }}
    >
      <BokehContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
