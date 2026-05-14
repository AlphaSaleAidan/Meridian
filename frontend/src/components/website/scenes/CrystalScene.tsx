import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

interface Crystal {
  x: number; y: number; z: number
  scale: number; speedX: number; speedY: number; detail: number
}

function Crystals({ accentColor }: { accentColor: string }) {
  const groupRef = useRef<THREE.Group>(null)
  const crystals = useMemo<Crystal[]>(() =>
    Array.from({ length: 7 }, () => ({
      x: (Math.random() - 0.5) * 7,
      y: (Math.random() - 0.5) * 4,
      z: (Math.random() - 0.5) * 3 - 1,
      scale: 0.3 + Math.random() * 0.5,
      speedX: 0.05 + Math.random() * 0.15,
      speedY: 0.08 + Math.random() * 0.2,
      detail: Math.floor(Math.random() * 2),
    }))
  , [])

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    groupRef.current.children.forEach((child, i) => {
      const c = crystals[i]
      child.rotation.x = t * c.speedX
      child.rotation.y = t * c.speedY
    })
  })

  return (
    <group ref={groupRef}>
      {crystals.map((c, i) => (
        <mesh key={i} position={[c.x, c.y, c.z]} scale={c.scale}>
          <dodecahedronGeometry args={[1, c.detail]} />
          <meshPhysicalMaterial
            color={accentColor}
            metalness={0.9}
            roughness={0.1}
            clearcoat={1.0}
            clearcoatRoughness={0.1}
          />
        </mesh>
      ))}
    </group>
  )
}

export default function CrystalScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 6], fov: 55 }}>
      <color attach="background" args={[primaryColor]} />
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 5, 5]} intensity={1.2} />
      <directionalLight position={[-3, -2, 4]} intensity={0.4} color={accentColor} />
      <pointLight position={[0, 0, 3]} intensity={0.6} color={accentColor} />
      <Crystals accentColor={accentColor} />
    </Canvas>
  )
}
