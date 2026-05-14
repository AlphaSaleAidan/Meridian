import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

interface ShapeData {
  x: number; y: number; z: number
  type: 'ico' | 'oct'
  scale: number; speedX: number; speedY: number
}

function Shapes({ accentColor }: { accentColor: string }) {
  const groupRef = useRef<THREE.Group>(null)
  const shapes = useMemo<ShapeData[]>(() =>
    Array.from({ length: 10 }, () => ({
      x: (Math.random() - 0.5) * 8,
      y: (Math.random() - 0.5) * 5,
      z: (Math.random() - 0.5) * 4 - 2,
      type: Math.random() > 0.5 ? 'ico' : 'oct',
      scale: 0.3 + Math.random() * 0.6,
      speedX: 0.1 + Math.random() * 0.4,
      speedY: 0.15 + Math.random() * 0.5,
    }))
  , [])

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    groupRef.current.children.forEach((child, i) => {
      const s = shapes[i]
      child.rotation.x = t * s.speedX
      child.rotation.y = t * s.speedY
    })
  })

  return (
    <group ref={groupRef}>
      {shapes.map((s, i) => (
        <mesh key={i} position={[s.x, s.y, s.z]} scale={s.scale}>
          {s.type === 'ico' ? <icosahedronGeometry args={[1, 0]} /> : <octahedronGeometry args={[1, 0]} />}
          <meshBasicMaterial color={accentColor} wireframe transparent opacity={0.5} />
        </mesh>
      ))}
    </group>
  )
}

export default function GeometricScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 7], fov: 55 }}>
      <color attach="background" args={[primaryColor]} />
      <Shapes accentColor={accentColor} />
    </Canvas>
  )
}
