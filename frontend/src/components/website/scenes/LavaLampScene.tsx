import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshDistortMaterial } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function LavaBlob({ position, scale, color, speed, distort, emissiveIntensity }: {
  position: [number, number, number]; scale: number; color: string
  speed: number; distort: number; emissiveIntensity: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime()
    ref.current.rotation.x = t * speed * 0.1
    ref.current.rotation.y = t * speed * 0.15
    ref.current.position.y = position[1] + Math.sin(t * speed * 0.4) * 1.2
    ref.current.position.x = position[0] + Math.cos(t * speed * 0.3) * 0.3
  })
  return (
    <Float speed={speed * 0.5} rotationIntensity={0.1} floatIntensity={0.2}>
      <mesh ref={ref} position={position} scale={scale}>
        <sphereGeometry args={[1, 96, 96]} />
        <MeshDistortMaterial
          color={color} emissive={color} emissiveIntensity={emissiveIntensity}
          metalness={0.3} roughness={0.4} distort={distort} speed={speed * 3}
        />
      </mesh>
    </Float>
  )
}

function HeatGlow({ position, color, scale }: {
  position: [number, number, number]; color: string; scale: number
}) {
  return (
    <mesh position={position} scale={scale}>
      <sphereGeometry args={[1, 16, 16]} />
      <meshBasicMaterial color={color} transparent opacity={0.03} toneMapped={false} blending={THREE.AdditiveBlending} />
    </mesh>
  )
}

function LavaContent({ primaryColor, accentColor }: SceneProps) {
  const blobs = useMemo(() => [
    { pos: [0, 0, 0] as [number, number, number], scale: 1.1, color: accentColor, speed: 0.5, distort: 0.45, emissive: 0.6 },
    { pos: [-1.5, -2, -1] as [number, number, number], scale: 0.7, color: primaryColor, speed: 0.7, distort: 0.5, emissive: 0.5 },
    { pos: [1.8, 1.5, -1.5] as [number, number, number], scale: 0.5, color: accentColor, speed: 0.9, distort: 0.55, emissive: 0.7 },
    { pos: [-0.8, 2, 0.5] as [number, number, number], scale: 0.4, color: primaryColor, speed: 1.1, distort: 0.4, emissive: 0.5 },
    { pos: [2, -1.5, -0.5] as [number, number, number], scale: 0.35, color: accentColor, speed: 0.8, distort: 0.5, emissive: 0.6 },
    { pos: [-2.5, 0.5, -2] as [number, number, number], scale: 0.3, color: primaryColor, speed: 1.0, distort: 0.45, emissive: 0.4 },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#080204']} />
      <fog attach="fog" args={['#080204', 3, 12]} />
      <ambientLight intensity={0.05} />
      <pointLight position={[3, 4, 3]} intensity={2} color={accentColor} distance={12} />
      <pointLight position={[-3, -3, 2]} intensity={1.5} color={primaryColor} distance={10} />
      <spotLight position={[0, -5, 3]} intensity={1} angle={0.6} penumbra={1} color={accentColor} />
      <HeatGlow position={[0, -1, -2]} color={accentColor} scale={5} />
      <HeatGlow position={[0, 2, -3]} color={primaryColor} scale={4} />
      {blobs.map((b, i) => (
        <LavaBlob key={i} position={b.pos} scale={b.scale} color={b.color}
          speed={b.speed} distort={b.distort} emissiveIntensity={b.emissive} />
      ))}
      <EffectComposer>
        <Bloom luminanceThreshold={0.2} luminanceSmoothing={0.9} intensity={1.8} />
      </EffectComposer>
    </>
  )
}

export default function LavaLampScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 5.5], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.6 }}
    >
      <LavaContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
