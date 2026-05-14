import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

interface Panel {
  x: number; y: number; z: number
  rx: number; ry: number; rz: number
  w: number; h: number; speed: number
}

function GlassPanels({ accentColor }: { accentColor: string }) {
  const groupRef = useRef<THREE.Group>(null)
  const panels = useMemo<Panel[]>(() =>
    Array.from({ length: 7 }, () => ({
      x: (Math.random() - 0.5) * 4,
      y: (Math.random() - 0.5) * 3,
      z: (Math.random() - 0.5) * 4 - 1,
      rx: Math.random() * 0.5,
      ry: Math.random() * 0.5,
      rz: Math.random() * 0.3,
      w: 1 + Math.random() * 2,
      h: 1 + Math.random() * 2,
      speed: 0.1 + Math.random() * 0.2,
    }))
  , [])

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    groupRef.current.children.forEach((child, i) => {
      const p = panels[i]
      child.rotation.x = p.rx + Math.sin(t * p.speed) * 0.15
      child.rotation.y = p.ry + Math.cos(t * p.speed * 0.8) * 0.15
      child.rotation.z = p.rz + Math.sin(t * p.speed * 0.5) * 0.05
    })
  })

  return (
    <group ref={groupRef}>
      {panels.map((p, i) => (
        <mesh key={i} position={[p.x, p.y, p.z]}>
          <planeGeometry args={[p.w, p.h]} />
          <meshPhysicalMaterial
            color={accentColor}
            transparent
            opacity={0.15}
            roughness={0.2}
            metalness={0.1}
            transmission={0.6}
            thickness={0.5}
            side={THREE.DoubleSide}
          />
        </mesh>
      ))}
    </group>
  )
}

export default function GlassMorphismScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 5], fov: 55 }}>
      <color attach="background" args={[primaryColor]} />
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 5, 5]} intensity={1} />
      <pointLight position={[-3, 2, 2]} intensity={0.5} color={accentColor} />
      <GlassPanels accentColor={accentColor} />
    </Canvas>
  )
}
