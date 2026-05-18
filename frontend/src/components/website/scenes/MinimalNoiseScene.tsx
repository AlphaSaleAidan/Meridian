import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function CenterSphere({ color }: { color: string }) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.y = clock.getElapsedTime() * 0.08
    ref.current.rotation.x = Math.sin(clock.getElapsedTime() * 0.05) * 0.1
  })
  return (
    <Float speed={0.4} rotationIntensity={0.05} floatIntensity={0.15}>
      <mesh ref={ref} scale={1.8}>
        <sphereGeometry args={[1, 128, 128]} />
        <MeshTransmissionMaterial
          backside thickness={0.6} chromaticAberration={0.06}
          color={color} roughness={0.0} transmission={0.98} ior={2.0}
          distortion={0.08} distortionScale={0.15} temporalDistortion={0.05}
          anisotropy={0.5}
        />
      </mesh>
    </Float>
  )
}

function SubtleDot({ position, color, scale, speed }: {
  position: [number, number, number]; color: string; scale: number; speed: number
}) {
  return (
    <Float speed={speed} floatIntensity={0.4}>
      <mesh position={position} scale={scale}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
    </Float>
  )
}

function MinimalContent({ primaryColor, accentColor }: SceneProps) {
  const dots = useMemo(() => [
    { pos: [3, 1.5, -4] as [number, number, number], color: accentColor, scale: 0.04, speed: 1.5 },
    { pos: [-2.5, -1, -3] as [number, number, number], color: primaryColor, scale: 0.03, speed: 1.8 },
    { pos: [1.5, -2, -5] as [number, number, number], color: accentColor, scale: 0.025, speed: 2.0 },
    { pos: [-1, 2.5, -3.5] as [number, number, number], color: primaryColor, scale: 0.035, speed: 1.3 },
    { pos: [2, 0.5, -6] as [number, number, number], color: accentColor, scale: 0.02, speed: 2.2 },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#060608']} />
      <fog attach="fog" args={['#060608', 5, 16]} />
      <ambientLight intensity={0.08} />
      <spotLight position={[4, 4, 4]} intensity={1.5} angle={0.3} penumbra={1} color={accentColor} />
      <spotLight position={[-3, -2, 3]} intensity={1} angle={0.4} penumbra={1} color={primaryColor} />
      <pointLight position={[0, 2, 3]} intensity={0.8} color="#ffffff" />
      <Environment preset="apartment" />
      <CenterSphere color={accentColor} />
      {dots.map((d, i) => (
        <SubtleDot key={i} position={d.pos} color={d.color} scale={d.scale} speed={d.speed} />
      ))}
      <EffectComposer>
        <Bloom luminanceThreshold={0.4} luminanceSmoothing={0.95} intensity={0.6} />
      </EffectComposer>
    </>
  )
}

export default function MinimalNoiseScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 5], fov: 45 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.2 }}
    >
      <MinimalContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
