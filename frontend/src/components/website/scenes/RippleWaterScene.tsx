import React, { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

function WaterSurface({ accentColor }: { accentColor: string }) {
  const ref = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    if (!ref.current) return
    const geo = ref.current.geometry
    const pos = geo.attributes.position
    const t = clock.getElapsedTime()
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i)
      const z = pos.getZ(i)
      const dist = Math.sqrt(x * x + z * z)
      pos.setY(i, Math.sin(dist * 2 - t * 3) * 0.15)
    }
    pos.needsUpdate = true
    geo.computeVertexNormals()
  })

  return (
    <mesh ref={ref} rotation={[-Math.PI / 2.5, 0, 0]} position={[0, -0.5, 0]}>
      <planeGeometry args={[16, 16, 80, 80]} />
      <meshStandardMaterial
        color={accentColor}
        metalness={0.7}
        roughness={0.2}
        side={THREE.DoubleSide}
        transparent
        opacity={0.8}
      />
    </mesh>
  )
}

export default function RippleWaterScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 4, 8], fov: 50 }}>
      <color attach="background" args={[primaryColor]} />
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 8, 5]} intensity={1} />
      <pointLight position={[-3, 3, -3]} intensity={0.4} color={accentColor} />
      <WaterSurface accentColor={accentColor} />
    </Canvas>
  )
}
