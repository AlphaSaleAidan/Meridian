import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshDistortMaterial, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function MetalBlob({ position, scale, color, speed, distort }: {
  position: [number, number, number]; scale: number; color: string; speed: number; distort: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.x = clock.getElapsedTime() * speed * 0.15
    ref.current.rotation.y = clock.getElapsedTime() * speed * 0.1
  })
  return (
    <Float speed={speed} rotationIntensity={0.2} floatIntensity={0.4}>
      <mesh ref={ref} position={position} scale={scale}>
        <sphereGeometry args={[1, 128, 128]} />
        <MeshDistortMaterial
          color={color} metalness={1} roughness={0.03}
          distort={distort} speed={speed * 2}
          envMapIntensity={3.5}
        />
      </mesh>
    </Float>
  )
}

function MetalRing({ position, scale, color, speed }: {
  position: [number, number, number]; scale: number; color: string; speed: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.x = clock.getElapsedTime() * speed * 0.3
    ref.current.rotation.z = clock.getElapsedTime() * speed * 0.2
  })
  return (
    <Float speed={speed * 1.5} rotationIntensity={0.15} floatIntensity={0.3}>
      <mesh ref={ref} position={position} scale={scale}>
        <torusGeometry args={[1, 0.08, 32, 64]} />
        <meshPhysicalMaterial
          color={color} metalness={1} roughness={0.02}
          envMapIntensity={3} clearcoat={1} clearcoatRoughness={0}
          iridescence={0.5} iridescenceIOR={1.3}
          iridescenceThicknessRange={[100, 400]}
        />
      </mesh>
    </Float>
  )
}

function MetalContent({ primaryColor, accentColor }: SceneProps) {
  const blobs = useMemo(() => [
    { pos: [0, 0, 0] as [number, number, number], scale: 1.3, color: accentColor, speed: 0.6, distort: 0.4 },
    { pos: [-2.5, 0.8, -1.5] as [number, number, number], scale: 0.5, color: primaryColor, speed: 0.9, distort: 0.5 },
    { pos: [2.2, -0.6, -1] as [number, number, number], scale: 0.4, color: accentColor, speed: 1.1, distort: 0.6 },
    { pos: [-1, -1.5, 0.5] as [number, number, number], scale: 0.3, color: primaryColor, speed: 1.3, distort: 0.5 },
    { pos: [1.5, 1.5, -2] as [number, number, number], scale: 0.35, color: accentColor, speed: 0.8, distort: 0.45 },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#020204']} />
      <fog attach="fog" args={['#020204', 4, 14]} />
      <ambientLight intensity={0.08} />
      <spotLight position={[5, 5, 5]} intensity={3} angle={0.4} penumbra={1} color={accentColor} />
      <spotLight position={[-5, -3, 3]} intensity={2} angle={0.5} penumbra={1} color={primaryColor} />
      <pointLight position={[0, 3, 2]} intensity={1.5} color="#ffffff" />
      <Environment preset="city" />
      {blobs.map((b, i) => (
        <MetalBlob key={i} position={b.pos} scale={b.scale} color={b.color} speed={b.speed} distort={b.distort} />
      ))}
      <MetalRing position={[0, 0, -0.5]} scale={2.2} color={accentColor} speed={0.3} />
      <MetalRing position={[-1.5, 1, -1]} scale={1.0} color={primaryColor} speed={0.5} />
      <MetalRing position={[2, -1, -1.5]} scale={0.8} color={accentColor} speed={0.4} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.35} luminanceSmoothing={0.8} intensity={1.0} />
      </EffectComposer>
    </>
  )
}

export default function LiquidMetalScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 5], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.5 }}
    >
      <MetalContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
