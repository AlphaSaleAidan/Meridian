import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function StarCloud({ count, spread, baseSize, color, speed }: {
  count: number; spread: number; baseSize: number; color: string; speed: number
}) {
  const ref = useRef<THREE.Points>(null)
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const r = spread * (0.3 + Math.random() * 0.7)
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pos[i * 3 + 2] = r * Math.cos(phi)
    }
    return pos
  }, [count, spread])

  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.y = clock.getElapsedTime() * speed * 0.02
    ref.current.rotation.x = Math.sin(clock.getElapsedTime() * speed * 0.01) * 0.05
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={count} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial color={color} size={baseSize} sizeAttenuation transparent opacity={0.9} blending={THREE.AdditiveBlending} />
    </points>
  )
}

function NebulaSphere({ position, color, scale }: {
  position: [number, number, number]; color: string; scale: number
}) {
  return (
    <Float speed={0.8} floatIntensity={0.5}>
      <mesh position={position} scale={scale}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.06} toneMapped={false} blending={THREE.AdditiveBlending} />
      </mesh>
    </Float>
  )
}

function GlowStar({ position, color, scale }: {
  position: [number, number, number]; color: string; scale: number
}) {
  return (
    <Float speed={1.5} floatIntensity={0.8}>
      <mesh position={position} scale={scale}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
    </Float>
  )
}

function StarfieldContent({ primaryColor, accentColor }: SceneProps) {
  return (
    <>
      <color attach="background" args={['#010104']} />
      <fog attach="fog" args={['#010104', 8, 40]} />
      <StarCloud count={4000} spread={25} baseSize={0.04} color="#ffffff" speed={1} />
      <StarCloud count={1500} spread={20} baseSize={0.06} color={accentColor} speed={0.7} />
      <StarCloud count={800} spread={15} baseSize={0.08} color={primaryColor} speed={1.3} />
      <NebulaSphere position={[5, 2, -10]} color={accentColor} scale={6} />
      <NebulaSphere position={[-6, -3, -8]} color={primaryColor} scale={5} />
      <NebulaSphere position={[0, 0, -12]} color={accentColor} scale={8} />
      <GlowStar position={[3, 1.5, -4]} color={accentColor} scale={0.08} />
      <GlowStar position={[-2, -1, -3]} color={primaryColor} scale={0.06} />
      <GlowStar position={[1, -2, -5]} color={accentColor} scale={0.05} />
      <GlowStar position={[-3, 2.5, -6]} color={primaryColor} scale={0.07} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.1} luminanceSmoothing={0.9} intensity={1.5} />
      </EffectComposer>
    </>
  )
}

export default function StarfieldScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 8], fov: 65 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.8 }}
    >
      <StarfieldContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
