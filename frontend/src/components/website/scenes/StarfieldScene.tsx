import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

function Starfield({ primaryColor, accentColor }: SceneProps) {
  const starsRef = useRef<THREE.Points>(null)
  const accentRef = useRef<THREE.Points>(null)
  const count = 5000
  const accentCount = 80

  const starPositions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const i3 = i * 3
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const r = 20 + Math.random() * 30
      pos[i3] = r * Math.sin(phi) * Math.cos(theta)
      pos[i3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pos[i3 + 2] = r * Math.cos(phi)
    }
    return pos
  }, [])

  const starSizes = useMemo(() => {
    const sizes = new Float32Array(count)
    for (let i = 0; i < count; i++) sizes[i] = 0.5 + Math.random() * 1.5
    return sizes
  }, [])

  const accentPositions = useMemo(() => {
    const pos = new Float32Array(accentCount * 3)
    for (let i = 0; i < accentCount; i++) {
      const i3 = i * 3
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const r = 15 + Math.random() * 25
      pos[i3] = r * Math.sin(phi) * Math.cos(theta)
      pos[i3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pos[i3 + 2] = r * Math.cos(phi)
    }
    return pos
  }, [])

  useFrame(({ clock, camera }) => {
    const t = clock.getElapsedTime()
    camera.position.z = 5 - (t * 0.5) % 40
    if (starsRef.current) {
      const sizes = starsRef.current.geometry.attributes.size.array as Float32Array
      for (let i = 0; i < count; i++) {
        sizes[i] = (0.5 + Math.random() * 1.5) * (0.8 + Math.sin(t * 3 + i * 0.1) * 0.2)
      }
      starsRef.current.geometry.attributes.size.needsUpdate = true
    }
  })

  return (
    <>
      <color attach="background" args={[primaryColor]} />
      <points ref={starsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[starPositions, 3]} count={count} itemSize={3} />
          <bufferAttribute attach="attributes-size" args={[starSizes, 1]} count={count} itemSize={1} />
        </bufferGeometry>
        <pointsMaterial color="#ffffff" size={0.08} sizeAttenuation transparent opacity={0.9} />
      </points>
      <points ref={accentRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[accentPositions, 3]} count={accentCount} itemSize={3} />
        </bufferGeometry>
        <pointsMaterial color={accentColor} size={0.2} sizeAttenuation transparent opacity={0.95} blending={THREE.AdditiveBlending} />
      </points>
    </>
  )
}

export default function StarfieldScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 5], fov: 75 }}>
      <Starfield primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
