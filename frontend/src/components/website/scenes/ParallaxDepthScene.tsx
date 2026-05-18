import { useRef, useMemo } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function FloatingRing({ position, scale, color, speed, metallic }: {
  position: [number, number, number]; scale: number; color: string; speed: number; metallic: boolean
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime() * speed
    ref.current.rotation.x = t * 0.3
    ref.current.rotation.z = t * 0.2
  })
  return (
    <Float speed={speed} rotationIntensity={0.15} floatIntensity={0.3}>
      <mesh ref={ref} position={position} scale={scale}>
        <torusGeometry args={[1, 0.15, 32, 64]} />
        {metallic ? (
          <meshPhysicalMaterial color={color} metalness={0.95} roughness={0.05} envMapIntensity={2} />
        ) : (
          <MeshTransmissionMaterial
            backside thickness={0.3} chromaticAberration={0.2}
            color={color} roughness={0.0} transmission={0.95} ior={1.5}
          />
        )}
      </mesh>
    </Float>
  )
}

function DepthParticles({ count, color, depth }: { count: number; color: string; depth: number }) {
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 12
      pos[i * 3 + 1] = (Math.random() - 0.5) * 8
      pos[i * 3 + 2] = -depth + (Math.random() - 0.5) * 2
    }
    return pos
  }, [count, depth])

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={count} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial color={color} size={0.03} sizeAttenuation transparent opacity={0.6} blending={THREE.AdditiveBlending} />
    </points>
  )
}

function ParallaxContent({ primaryColor, accentColor }: SceneProps) {
  const groupRef = useRef<THREE.Group>(null)
  const { pointer } = useThree()

  useFrame(() => {
    if (!groupRef.current) return
    groupRef.current.rotation.y += (pointer.x * 0.08 - groupRef.current.rotation.y) * 0.05
    groupRef.current.rotation.x += (pointer.y * 0.04 - groupRef.current.rotation.x) * 0.05
  })

  const rings = useMemo(() => [
    { pos: [0, 0, 0] as [number, number, number], scale: 1.2, color: accentColor, speed: 0.5, metallic: false },
    { pos: [-2.5, 1, -2] as [number, number, number], scale: 0.7, color: primaryColor, speed: 0.7, metallic: true },
    { pos: [2.2, -0.8, -3] as [number, number, number], scale: 0.6, color: accentColor, speed: 0.9, metallic: false },
    { pos: [-1, -1.5, -1] as [number, number, number], scale: 0.5, color: primaryColor, speed: 0.6, metallic: true },
    { pos: [1.5, 1.5, -4] as [number, number, number], scale: 0.8, color: accentColor, speed: 0.8, metallic: false },
    { pos: [0.5, -0.5, -5] as [number, number, number], scale: 0.4, color: primaryColor, speed: 1.0, metallic: true },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#030306']} />
      <fog attach="fog" args={['#030306', 3, 16]} />
      <ambientLight intensity={0.08} />
      <spotLight position={[4, 3, 3]} intensity={2} angle={0.4} penumbra={1} color={accentColor} />
      <spotLight position={[-3, -2, 4]} intensity={1.5} angle={0.5} penumbra={1} color={primaryColor} />
      <pointLight position={[0, 2, 2]} intensity={1} color="#ffffff" />
      <Environment preset="city" />
      <group ref={groupRef}>
        {rings.map((r, i) => (
          <FloatingRing key={i} position={r.pos} scale={r.scale} color={r.color} speed={r.speed} metallic={r.metallic} />
        ))}
        <DepthParticles count={500} color={accentColor} depth={3} />
        <DepthParticles count={300} color={primaryColor} depth={6} />
        <DepthParticles count={200} color="#ffffff" depth={9} />
      </group>
      <EffectComposer>
        <Bloom luminanceThreshold={0.3} luminanceSmoothing={0.85} intensity={1.0} />
      </EffectComposer>
    </>
  )
}

export default function ParallaxDepthScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 6], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.4 }}
    >
      <ParallaxContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
