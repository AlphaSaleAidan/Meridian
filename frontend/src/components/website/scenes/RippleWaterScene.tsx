import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function WaterPlane({ color }: { color: string }) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const geo = ref.current.geometry
    const pos = geo.attributes.position
    const t = clock.getElapsedTime()
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i)
      const z = pos.getZ(i)
      const d = Math.sqrt(x * x + z * z)
      pos.setY(i,
        Math.sin(d * 1.5 - t * 2) * 0.12 +
        Math.sin(x * 2 + t * 1.5) * 0.06 +
        Math.cos(z * 1.8 + t * 1.2) * 0.05
      )
    }
    pos.needsUpdate = true
    geo.computeVertexNormals()
  })
  return (
    <mesh ref={ref} rotation={[-Math.PI / 2.2, 0, 0]} position={[0, -1.2, 0]}>
      <planeGeometry args={[20, 20, 100, 100]} />
      <meshPhysicalMaterial
        color={color} metalness={0.85} roughness={0.1}
        envMapIntensity={2} transparent opacity={0.9}
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}

function FloatingGem({ position, scale, color, speed }: {
  position: [number, number, number]; scale: number; color: string; speed: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime() * speed
    ref.current.rotation.x = t * 0.4
    ref.current.rotation.y = t * 0.3
  })
  return (
    <Float speed={speed} rotationIntensity={0.2} floatIntensity={0.5}>
      <mesh ref={ref} position={position} scale={scale}>
        <octahedronGeometry args={[1, 0]} />
        <MeshTransmissionMaterial
          backside thickness={0.4} chromaticAberration={0.3}
          color={color} roughness={0.0} transmission={0.95} ior={1.8}
          distortion={0.1} distortionScale={0.2}
        />
      </mesh>
    </Float>
  )
}

function WaterContent({ primaryColor, accentColor }: SceneProps) {
  const gems = useMemo(() => [
    { pos: [0, 0.8, 0] as [number, number, number], scale: 0.5, color: accentColor, speed: 0.6 },
    { pos: [-2, 0.3, -1] as [number, number, number], scale: 0.3, color: primaryColor, speed: 0.8 },
    { pos: [2.5, 1, -1.5] as [number, number, number], scale: 0.35, color: accentColor, speed: 0.7 },
    { pos: [-1.5, 1.5, 1] as [number, number, number], scale: 0.25, color: primaryColor, speed: 0.9 },
    { pos: [1, 0.5, 1.5] as [number, number, number], scale: 0.2, color: accentColor, speed: 1.0 },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#020208']} />
      <fog attach="fog" args={['#020208', 5, 18]} />
      <ambientLight intensity={0.1} />
      <spotLight position={[5, 8, 5]} intensity={3} angle={0.3} penumbra={1} color={accentColor} />
      <spotLight position={[-4, 5, 3]} intensity={2} angle={0.4} penumbra={1} color={primaryColor} />
      <pointLight position={[0, 4, 0]} intensity={1.5} color="#ffffff" />
      <Environment preset="city" />
      <WaterPlane color={accentColor} />
      {gems.map((g, i) => (
        <FloatingGem key={i} position={g.pos} scale={g.scale} color={g.color} speed={g.speed} />
      ))}
      <EffectComposer>
        <Bloom luminanceThreshold={0.3} luminanceSmoothing={0.85} intensity={1.0} />
      </EffectComposer>
    </>
  )
}

export default function RippleWaterScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 3, 7], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.4 }}
    >
      <WaterContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
