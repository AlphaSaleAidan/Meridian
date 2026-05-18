import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshDistortMaterial, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function MorphBlob({ position, scale, color, speed, distort, metalness }: {
  position: [number, number, number]; scale: number; color: string
  speed: number; distort: number; metalness: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime()
    ref.current.rotation.x = t * speed * 0.12
    ref.current.rotation.y = t * speed * 0.18
    ref.current.rotation.z = Math.sin(t * speed * 0.1) * 0.3
  })
  return (
    <Float speed={speed * 0.8} rotationIntensity={0.15} floatIntensity={0.4}>
      <mesh ref={ref} position={position} scale={scale}>
        <sphereGeometry args={[1, 128, 128]} />
        <MeshDistortMaterial
          color={color} metalness={metalness} roughness={0.08}
          distort={distort} speed={speed * 2.5}
          envMapIntensity={2.5}
        />
      </mesh>
    </Float>
  )
}

function MorphContent({ primaryColor, accentColor }: SceneProps) {
  const blobs = useMemo(() => [
    { pos: [0, 0, 0] as [number, number, number], scale: 1.6, color: accentColor, speed: 0.5, distort: 0.5, metalness: 0.95 },
    { pos: [-2.8, 1, -2] as [number, number, number], scale: 0.5, color: primaryColor, speed: 0.8, distort: 0.6, metalness: 0.9 },
    { pos: [2.5, -0.8, -1.5] as [number, number, number], scale: 0.4, color: accentColor, speed: 1.0, distort: 0.55, metalness: 0.85 },
    { pos: [-1.5, -1.5, 0.5] as [number, number, number], scale: 0.3, color: primaryColor, speed: 1.2, distort: 0.5, metalness: 0.9 },
    { pos: [1.8, 1.8, -2.5] as [number, number, number], scale: 0.35, color: accentColor, speed: 0.7, distort: 0.45, metalness: 0.95 },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#020206']} />
      <fog attach="fog" args={['#020206', 4, 14]} />
      <ambientLight intensity={0.08} />
      <spotLight position={[5, 5, 5]} intensity={3} angle={0.4} penumbra={1} color={accentColor} />
      <spotLight position={[-5, -3, 4]} intensity={2} angle={0.5} penumbra={1} color={primaryColor} />
      <pointLight position={[0, 3, 2]} intensity={1.5} color="#ffffff" />
      <Environment preset="night" />
      {blobs.map((b, i) => (
        <MorphBlob key={i} position={b.pos} scale={b.scale} color={b.color}
          speed={b.speed} distort={b.distort} metalness={b.metalness} />
      ))}
      <EffectComposer>
        <Bloom luminanceThreshold={0.35} luminanceSmoothing={0.8} intensity={1.0} />
      </EffectComposer>
    </>
  )
}

export default function MorphingBlobScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 5], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.5 }}
    >
      <MorphContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
