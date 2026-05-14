import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { MeshDistortMaterial } from '@react-three/drei'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

interface Blob {
  x: number; y: number; z: number
  scale: number; phase: number; speed: number
}

function LavaBlobs({ accentColor }: { accentColor: string }) {
  const groupRef = useRef<THREE.Group>(null)
  const blobs = useMemo<Blob[]>(() =>
    Array.from({ length: 5 }, (_, i) => ({
      x: (Math.random() - 0.5) * 3,
      y: (i - 2) * 1.5,
      z: (Math.random() - 0.5) * 2,
      scale: 0.5 + Math.random() * 0.5,
      phase: Math.random() * Math.PI * 2,
      speed: 0.3 + Math.random() * 0.4,
    }))
  , [])

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    groupRef.current.children.forEach((child, i) => {
      const b = blobs[i]
      child.position.y = b.y + Math.sin(t * b.speed + b.phase) * 1.5
      child.position.x = b.x + Math.cos(t * b.speed * 0.7 + b.phase) * 0.3
    })
  })

  return (
    <group ref={groupRef}>
      {blobs.map((b, i) => (
        <mesh key={i} position={[b.x, b.y, b.z]} scale={b.scale}>
          <sphereGeometry args={[1, 32, 32]} />
          <MeshDistortMaterial color={accentColor} emissive={accentColor} emissiveIntensity={0.3} distort={0.3} speed={2} roughness={0.4} />
        </mesh>
      ))}
    </group>
  )
}

export default function LavaLampScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 6], fov: 55 }}>
      <color attach="background" args={[primaryColor]} />
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 5, 5]} intensity={0.8} />
      <pointLight position={[0, 0, 3]} intensity={0.5} color={accentColor} />
      <LavaBlobs accentColor={accentColor} />
    </Canvas>
  )
}
