import React, { useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

interface FogSphere {
  x: number; y: number; z: number
  scale: number; speed: number; phase: number
}

function FogSetup({ primaryColor }: { primaryColor: string }) {
  const { scene } = useThree()
  useEffect(() => {
    scene.fog = new THREE.FogExp2(primaryColor, 0.12)
    return () => { scene.fog = null }
  }, [scene, primaryColor])
  return null
}

function DriftingSpheres({ accentColor }: { accentColor: string }) {
  const groupRef = useRef<THREE.Group>(null)
  const spheres = useMemo<FogSphere[]>(() =>
    Array.from({ length: 15 }, () => ({
      x: (Math.random() - 0.5) * 12,
      y: (Math.random() - 0.5) * 6,
      z: -Math.random() * 10 - 2,
      scale: 0.8 + Math.random() * 2,
      speed: 0.05 + Math.random() * 0.15,
      phase: Math.random() * Math.PI * 2,
    }))
  , [])

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    const t = clock.getElapsedTime()
    groupRef.current.children.forEach((child, i) => {
      const s = spheres[i]
      child.position.x = s.x + Math.sin(t * s.speed + s.phase) * 1.5
      child.position.y = s.y + Math.cos(t * s.speed * 0.7 + s.phase) * 0.8
      const mat = (child as THREE.Mesh).material as THREE.MeshStandardMaterial
      mat.opacity = 0.1 + Math.sin(t * 0.3 + s.phase) * 0.08
    })
  })

  return (
    <group ref={groupRef}>
      {spheres.map((s, i) => (
        <mesh key={i} position={[s.x, s.y, s.z]} scale={s.scale}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshStandardMaterial color={accentColor} transparent opacity={0.15} depthWrite={false} />
        </mesh>
      ))}
    </group>
  )
}

export default function FogDarkScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 5], fov: 60 }}>
      <color attach="background" args={[primaryColor]} />
      <FogSetup primaryColor={primaryColor} />
      <ambientLight intensity={0.15} />
      <pointLight position={[3, 2, 4]} intensity={0.3} color={accentColor} />
      <DriftingSpheres accentColor={accentColor} />
    </Canvas>
  )
}
