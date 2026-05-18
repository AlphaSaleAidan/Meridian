import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function FogOrb({ position, scale, color, speed, glow }: {
  position: [number, number, number]; scale: number; color: string; speed: number; glow: boolean
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.y = clock.getElapsedTime() * speed * 0.1
  })
  return (
    <Float speed={speed} rotationIntensity={0.1} floatIntensity={0.5}>
      <mesh ref={ref} position={position} scale={scale}>
        <sphereGeometry args={[1, 48, 48]} />
        {glow ? (
          <meshBasicMaterial color={color} toneMapped={false} />
        ) : (
          <MeshTransmissionMaterial
            backside thickness={0.5} chromaticAberration={0.2}
            color={color} roughness={0.1} transmission={0.9} ior={1.4}
            distortion={0.15} distortionScale={0.3} temporalDistortion={0.1}
          />
        )}
      </mesh>
      {glow && (
        <mesh position={position} scale={scale * 3}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshBasicMaterial color={color} transparent opacity={0.04} toneMapped={false} blending={THREE.AdditiveBlending} />
        </mesh>
      )}
    </Float>
  )
}

function FogDarkContent({ primaryColor, accentColor }: SceneProps) {
  const orbs = useMemo(() => [
    { pos: [0, 0, -1] as [number, number, number], scale: 0.12, color: accentColor, speed: 1.0, glow: true },
    { pos: [-3, 1.5, -4] as [number, number, number], scale: 0.6, color: primaryColor, speed: 0.6, glow: false },
    { pos: [2.5, -0.5, -3] as [number, number, number], scale: 0.5, color: accentColor, speed: 0.8, glow: false },
    { pos: [-1.5, -1.8, -2] as [number, number, number], scale: 0.08, color: primaryColor, speed: 1.5, glow: true },
    { pos: [3, 2, -5] as [number, number, number], scale: 0.45, color: accentColor, speed: 0.7, glow: false },
    { pos: [-2, 0.5, -2.5] as [number, number, number], scale: 0.06, color: accentColor, speed: 1.8, glow: true },
    { pos: [1, 1.5, -3.5] as [number, number, number], scale: 0.35, color: primaryColor, speed: 0.9, glow: false },
    { pos: [0.5, -2, -4] as [number, number, number], scale: 0.07, color: primaryColor, speed: 1.3, glow: true },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#010103']} />
      <fog attach="fog" args={['#010103', 2, 10]} />
      <ambientLight intensity={0.03} />
      <pointLight position={[3, 3, 2]} intensity={1.5} color={accentColor} distance={12} />
      <pointLight position={[-3, -2, 3]} intensity={1} color={primaryColor} distance={10} />
      {orbs.map((o, i) => (
        <FogOrb key={i} position={o.pos} scale={o.scale} color={o.color} speed={o.speed} glow={o.glow} />
      ))}
      <EffectComposer>
        <Bloom luminanceThreshold={0.08} luminanceSmoothing={0.95} intensity={2.0} />
      </EffectComposer>
    </>
  )
}

export default function FogDarkScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 5], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.8 }}
    >
      <FogDarkContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
