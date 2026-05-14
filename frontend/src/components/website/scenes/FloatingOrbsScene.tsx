import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

interface Orb {
  x: number; y: number; z: number
  size: number; speedX: number; speedY: number; phase: number
}

function Orbs({ accentColor }: { accentColor: string }) {
  const groupRef = useRef<THREE.Group>(null)
  const orbs = useMemo<Orb[]>(() =>
    Array.from({ length: 14 }, () => ({
      x: (Math.random() - 0.5) * 8,
      y: (Math.random() - 0.5) * 5,
      z: (Math.random() - 0.5) * 4 - 1,
      size: 0.15 + Math.random() * 0.35,
      speedX: 0.2 + Math.random() * 0.4,
      speedY: 0.15 + Math.random() * 0.3,
      phase: Math.random() * Math.PI * 2,
    }))
  , [])

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    groupRef.current.children.forEach((group, i) => {
      const o = orbs[i]
      group.position.x = o.x + Math.sin(t * o.speedX + o.phase) * 1.5
      group.position.y = o.y + Math.cos(t * o.speedY + o.phase) * 1.0
    })
  })

  return (
    <group ref={groupRef}>
      {orbs.map((o, i) => (
        <group key={i} position={[o.x, o.y, o.z]}>
          <mesh>
            <sphereGeometry args={[o.size, 20, 20]} />
            <meshStandardMaterial color={accentColor} emissive={accentColor} emissiveIntensity={0.8} />
          </mesh>
          <mesh>
            <sphereGeometry args={[o.size * 1.8, 16, 16]} />
            <meshBasicMaterial color={accentColor} transparent opacity={0.08} depthWrite={false} />
          </mesh>
        </group>
      ))}
    </group>
  )
}

export default function FloatingOrbsScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 7], fov: 55 }}>
      <color attach="background" args={[primaryColor]} />
      <ambientLight intensity={0.3} />
      <pointLight position={[5, 5, 5]} intensity={0.5} />
      <Orbs accentColor={accentColor} />
    </Canvas>
  )
}
