import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function SpiralCloud({ count, color, radius, speed, ySpread, size }: {
  count: number; color: string; radius: number; speed: number; ySpread: number; size: number
}) {
  const ref = useRef<THREE.Points>(null)
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const t = (i / count) * Math.PI * 8
      const r = radius * (0.2 + (i / count) * 0.8)
      const scatter = (Math.random() - 0.5) * 0.8
      pos[i * 3] = Math.cos(t) * r + scatter
      pos[i * 3 + 1] = (Math.random() - 0.5) * ySpread
      pos[i * 3 + 2] = Math.sin(t) * r + scatter
    }
    return pos
  }, [count, radius, ySpread])

  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.y = clock.getElapsedTime() * speed * 0.05
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={count} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial color={color} size={size} sizeAttenuation transparent opacity={0.85} blending={THREE.AdditiveBlending} />
    </points>
  )
}

function CoreGlow({ color, scale }: { color: string; scale: number }) {
  return (
    <Float speed={1} floatIntensity={0.3}>
      <mesh scale={scale}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.15} toneMapped={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh scale={scale * 0.4}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
    </Float>
  )
}

function ParticlesContent({ primaryColor, accentColor }: SceneProps) {
  return (
    <>
      <color attach="background" args={['#020204']} />
      <fog attach="fog" args={['#020204', 5, 20]} />
      <SpiralCloud count={3000} color="#ffffff" radius={4} speed={1} ySpread={3} size={0.025} />
      <SpiralCloud count={1500} color={accentColor} radius={3} speed={0.8} ySpread={2} size={0.04} />
      <SpiralCloud count={800} color={primaryColor} radius={5} speed={1.2} ySpread={4} size={0.05} />
      <CoreGlow color={accentColor} scale={1.2} />
      <Float speed={1.5} floatIntensity={0.6}>
        <mesh position={[3, 1.5, -2]} scale={0.06}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshBasicMaterial color={accentColor} toneMapped={false} />
        </mesh>
      </Float>
      <Float speed={1.8} floatIntensity={0.5}>
        <mesh position={[-2.5, -1, -3]} scale={0.05}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshBasicMaterial color={primaryColor} toneMapped={false} />
        </mesh>
      </Float>
      <EffectComposer>
        <Bloom luminanceThreshold={0.1} luminanceSmoothing={0.9} intensity={1.5} />
      </EffectComposer>
    </>
  )
}

export default function ParticlesScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 2, 7], fov: 55 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.6 }}
    >
      <ParticlesContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
