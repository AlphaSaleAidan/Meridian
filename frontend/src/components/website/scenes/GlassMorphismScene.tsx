import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial, RoundedBox, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function GlassPanel({ position, rotation, scale, color, speed }: {
  position: [number, number, number]; rotation: [number, number, number]
  scale: [number, number, number]; color: string; speed: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime() * speed
    ref.current.rotation.x = rotation[0] + Math.sin(t * 0.5) * 0.05
    ref.current.rotation.y = rotation[1] + Math.sin(t * 0.3) * 0.05
  })
  return (
    <Float speed={speed * 1.5} rotationIntensity={0.1} floatIntensity={0.3}>
      <RoundedBox ref={ref} args={scale} radius={0.05} position={position} rotation={rotation}>
        <MeshTransmissionMaterial
          backside thickness={0.15} chromaticAberration={0.12}
          color={color} roughness={0.08} transmission={0.92} ior={1.25}
          distortion={0} distortionScale={0}
          anisotropy={0.5}
        />
      </RoundedBox>
    </Float>
  )
}

function GlowOrb({ position, color, scale }: { position: [number, number, number]; color: string; scale: number }) {
  return (
    <Float speed={2} floatIntensity={1}>
      <mesh position={position} scale={scale}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
    </Float>
  )
}

function IridescentSphere({ position, scale, color, speed }: {
  position: [number, number, number]; scale: number; color: string; speed: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * speed * 0.2
  })
  return (
    <Float speed={speed} rotationIntensity={0.1} floatIntensity={0.4}>
      <mesh ref={ref} position={position} scale={scale}>
        <sphereGeometry args={[1, 48, 48]} />
        <meshPhysicalMaterial
          color={color} metalness={0.2} roughness={0.02}
          transmission={0.8} thickness={0.3} ior={1.5}
          iridescence={1} iridescenceIOR={1.5}
          iridescenceThicknessRange={[100, 600]}
          clearcoat={1} clearcoatRoughness={0}
          sheen={0.5} sheenRoughness={0.2} sheenColor={new THREE.Color(color)}
        />
      </mesh>
    </Float>
  )
}

function GlassContent({ primaryColor, accentColor }: SceneProps) {
  const panels = useMemo(() => [
    { pos: [0, 0, 0] as [number, number, number], rot: [0.1, 0.2, 0.05] as [number, number, number], scale: [2.5, 1.8, 0.05] as [number, number, number], color: accentColor, speed: 0.5 },
    { pos: [-1.5, 0.8, -0.8] as [number, number, number], rot: [-0.1, -0.3, 0.1] as [number, number, number], scale: [1.8, 1.3, 0.04] as [number, number, number], color: primaryColor, speed: 0.7 },
    { pos: [1.8, -0.5, -1.2] as [number, number, number], rot: [0.05, 0.4, -0.05] as [number, number, number], scale: [1.5, 2, 0.04] as [number, number, number], color: accentColor, speed: 0.6 },
    { pos: [-0.5, -1.2, 0.5] as [number, number, number], rot: [0.2, -0.1, 0.15] as [number, number, number], scale: [2, 1, 0.03] as [number, number, number], color: primaryColor, speed: 0.8 },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#040408']} />
      <fog attach="fog" args={['#040408', 3, 12]} />
      <ambientLight intensity={0.08} />
      <pointLight position={[3, 3, 3]} intensity={2.5} color={accentColor} />
      <pointLight position={[-3, -2, 2]} intensity={1.5} color={primaryColor} />
      <Environment preset="apartment" />
      <GlowOrb position={[2, 1.5, -2]} color={accentColor} scale={0.15} />
      <GlowOrb position={[-2, -1, -1.5]} color={primaryColor} scale={0.12} />
      <GlowOrb position={[0.5, -2, -1]} color={accentColor} scale={0.1} />
      <IridescentSphere position={[-2.5, 1.5, -1]} scale={0.25} color={accentColor} speed={0.8} />
      <IridescentSphere position={[2.8, -1.2, -0.5]} scale={0.2} color={primaryColor} speed={1.0} />
      {panels.map((p, i) => (
        <GlassPanel key={i} position={p.pos} rotation={p.rot} scale={p.scale} color={p.color} speed={p.speed} />
      ))}
      <EffectComposer>
        <Bloom luminanceThreshold={0.25} luminanceSmoothing={0.9} intensity={1.2} />
      </EffectComposer>
    </>
  )
}

export default function GlassMorphismScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 5], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.3 }}
    >
      <GlassContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
