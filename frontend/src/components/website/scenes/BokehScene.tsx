import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

interface Circle {
  x: number; y: number; z: number
  size: number; speed: number; phase: number; opacity: number
}

function BokehCircles({ accentColor }: { accentColor: string }) {
  const groupRef = useRef<THREE.Group>(null)
  const circles = useMemo<Circle[]>(() =>
    Array.from({ length: 50 }, () => ({
      x: (Math.random() - 0.5) * 10,
      y: (Math.random() - 0.5) * 8 - 2,
      z: (Math.random() - 0.5) * 6 - 2,
      size: 0.1 + Math.random() * 0.7,
      speed: 0.1 + Math.random() * 0.3,
      phase: Math.random() * Math.PI * 2,
      opacity: 0.1 + Math.random() * 0.3,
    }))
  , [])

  const texture = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 64
    canvas.height = 64
    const ctx = canvas.getContext('2d')!
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32)
    gradient.addColorStop(0, 'rgba(255,255,255,1)')
    gradient.addColorStop(0.4, 'rgba(255,255,255,0.5)')
    gradient.addColorStop(1, 'rgba(255,255,255,0)')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, 64, 64)
    const tex = new THREE.CanvasTexture(canvas)
    return tex
  }, [])

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    groupRef.current.children.forEach((child, i) => {
      const c = circles[i]
      child.position.y = c.y + ((t * c.speed + c.phase) % 10) - 2
      if (child.position.y > 5) child.position.y -= 10
      const mat = (child as THREE.Sprite).material as THREE.SpriteMaterial
      mat.opacity = c.opacity * (0.7 + Math.sin(t * 2 + c.phase) * 0.3)
    })
  })

  return (
    <group ref={groupRef}>
      {circles.map((c, i) => (
        <sprite key={i} position={[c.x, c.y, c.z]} scale={[c.size, c.size, 1]}>
          <spriteMaterial map={texture} color={accentColor} transparent opacity={c.opacity} depthWrite={false} blending={THREE.AdditiveBlending} />
        </sprite>
      ))}
    </group>
  )
}

export default function BokehScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 5], fov: 60 }}>
      <color attach="background" args={[primaryColor]} />
      <BokehCircles accentColor={accentColor} />
    </Canvas>
  )
}
