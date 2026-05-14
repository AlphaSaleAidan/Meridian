import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

function ParticleCloud({ primaryColor, accentColor }: SceneProps) {
  const ref = useRef<THREE.Points>(null)
  const count = 3000

  const { positions, colors } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    const c1 = new THREE.Color(primaryColor)
    const c2 = new THREE.Color(accentColor)
    for (let i = 0; i < count; i++) {
      const i3 = i * 3
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const r = 2 + Math.random() * 2
      pos[i3] = r * Math.sin(phi) * Math.cos(theta)
      pos[i3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pos[i3 + 2] = r * Math.cos(phi)
      const t = Math.random()
      col[i3] = c1.r + (c2.r - c1.r) * t
      col[i3 + 1] = c1.g + (c2.g - c1.g) * t
      col[i3 + 2] = c1.b + (c2.b - c1.b) * t
    }
    return { positions: pos, colors: col }
  }, [primaryColor, accentColor])

  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.y = clock.getElapsedTime() * 0.08
    ref.current.rotation.x = Math.sin(clock.getElapsedTime() * 0.05) * 0.1
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={count} itemSize={3} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} count={count} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.04} vertexColors sizeAttenuation transparent opacity={0.85} blending={THREE.AdditiveBlending} />
    </points>
  )
}

export default function ParticlesScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 6], fov: 60 }}>
      <color attach="background" args={[primaryColor]} />
      <ParticleCloud primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
