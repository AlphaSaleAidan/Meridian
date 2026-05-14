import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

interface Puff {
  x: number; y: number; z: number
  scale: number; speed: number; phase: number; opacity: number
}

function SmokePuffs({ accentColor }: { accentColor: string }) {
  const groupRef = useRef<THREE.Group>(null)
  const puffs = useMemo<Puff[]>(() => {
    return Array.from({ length: 20 }, () => ({
      x: (Math.random() - 0.5) * 8,
      y: (Math.random() - 0.5) * 4,
      z: (Math.random() - 0.5) * 4 - 2,
      scale: 0.8 + Math.random() * 1.5,
      speed: 0.1 + Math.random() * 0.3,
      phase: Math.random() * Math.PI * 2,
      opacity: 0.15 + Math.random() * 0.15,
    }))
  }, [])

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    groupRef.current.children.forEach((child, i) => {
      const p = puffs[i]
      child.position.x = p.x + Math.sin(t * p.speed + p.phase) * 0.5
      child.position.y = p.y + Math.cos(t * p.speed * 0.7 + p.phase) * 0.3
      const s = p.scale + Math.sin(t * 0.5 + p.phase) * 0.2
      child.scale.setScalar(s)
    })
  })

  return (
    <group ref={groupRef}>
      {puffs.map((p, i) => (
        <mesh key={i} position={[p.x, p.y, p.z]}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshStandardMaterial color={accentColor} transparent opacity={p.opacity} depthWrite={false} />
        </mesh>
      ))}
    </group>
  )
}

export default function SmokeScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 6], fov: 60 }}>
      <color attach="background" args={[primaryColor]} />
      <ambientLight intensity={0.4} />
      <pointLight position={[3, 3, 3]} intensity={0.6} />
      <SmokePuffs accentColor={accentColor} />
    </Canvas>
  )
}
