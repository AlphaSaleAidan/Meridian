import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function GeoShape({ position, scale, color, speed, shape, metallic }: {
  position: [number, number, number]; scale: number; color: string
  speed: number; shape: 'ico' | 'oct' | 'dodeca' | 'torus'; metallic: boolean
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime() * speed
    ref.current.rotation.x = t * 0.3
    ref.current.rotation.y = t * 0.2
    ref.current.rotation.z = Math.sin(t * 0.15) * 0.5
  })
  return (
    <Float speed={speed * 1.5} rotationIntensity={0.2} floatIntensity={0.4}>
      <mesh ref={ref} position={position} scale={scale}>
        {shape === 'ico' && <icosahedronGeometry args={[1, 0]} />}
        {shape === 'oct' && <octahedronGeometry args={[1, 0]} />}
        {shape === 'dodeca' && <dodecahedronGeometry args={[1, 0]} />}
        {shape === 'torus' && <torusGeometry args={[1, 0.4, 16, 32]} />}
        {metallic ? (
          <meshPhysicalMaterial color={color} metalness={0.95} roughness={0.05} envMapIntensity={2.5} />
        ) : (
          <MeshTransmissionMaterial
            backside thickness={0.4} chromaticAberration={0.25}
            color={color} roughness={0.0} transmission={0.95} ior={1.5}
            distortion={0.1} distortionScale={0.2}
          />
        )}
      </mesh>
    </Float>
  )
}

function GeoContent({ primaryColor, accentColor }: SceneProps) {
  const shapes = useMemo(() => [
    { pos: [0, 0, 0] as [number, number, number], scale: 1.0, color: accentColor, speed: 0.5, shape: 'ico' as const, metallic: false },
    { pos: [-2.5, 1.2, -1.5] as [number, number, number], scale: 0.6, color: primaryColor, speed: 0.7, shape: 'oct' as const, metallic: true },
    { pos: [2.2, -0.8, -1] as [number, number, number], scale: 0.5, color: accentColor, speed: 0.9, shape: 'dodeca' as const, metallic: false },
    { pos: [-1.2, -1.5, 0.5] as [number, number, number], scale: 0.4, color: primaryColor, speed: 0.6, shape: 'torus' as const, metallic: true },
    { pos: [1.8, 1.5, -2] as [number, number, number], scale: 0.55, color: accentColor, speed: 0.8, shape: 'oct' as const, metallic: false },
    { pos: [3, -1.5, -1.5] as [number, number, number], scale: 0.3, color: primaryColor, speed: 1.0, shape: 'ico' as const, metallic: true },
    { pos: [-0.5, 2, -1] as [number, number, number], scale: 0.35, color: accentColor, speed: 1.1, shape: 'dodeca' as const, metallic: true },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#030308']} />
      <fog attach="fog" args={['#030308', 4, 14]} />
      <ambientLight intensity={0.1} />
      <spotLight position={[5, 4, 4]} intensity={2.5} angle={0.4} penumbra={1} color={accentColor} />
      <spotLight position={[-4, -3, 3]} intensity={2} angle={0.5} penumbra={1} color={primaryColor} />
      <pointLight position={[0, 3, 2]} intensity={1} color="#ffffff" />
      <Environment preset="city" />
      {shapes.map((s, i) => (
        <GeoShape key={i} position={s.pos} scale={s.scale} color={s.color}
          speed={s.speed} shape={s.shape} metallic={s.metallic} />
      ))}
      <EffectComposer>
        <Bloom luminanceThreshold={0.3} luminanceSmoothing={0.85} intensity={1.0} />
      </EffectComposer>
    </>
  )
}

export default function GeometricScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 5.5], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.3 }}
    >
      <GeoContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
