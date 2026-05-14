import React, { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

function WaveMesh({ accentColor }: { accentColor: string }) {
  const ref = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    if (!ref.current) return
    const geo = ref.current.geometry
    const pos = geo.attributes.position
    const t = clock.getElapsedTime()
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i)
      const z = pos.getZ(i)
      pos.setY(i, Math.sin(x * 0.3 + t) * Math.cos(z * 0.3 + t) * 0.8)
    }
    pos.needsUpdate = true
    geo.computeVertexNormals()
  })

  return (
    <mesh ref={ref} rotation={[-Math.PI / 3, 0, 0]} position={[0, -1, 0]}>
      <planeGeometry args={[16, 16, 64, 64]} />
      <meshStandardMaterial color={accentColor} wireframe transparent opacity={0.6} side={THREE.DoubleSide} />
    </mesh>
  )
}

export default function WavesScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 3, 8], fov: 55 }}>
      <color attach="background" args={[primaryColor]} />
      <ambientLight intensity={0.5} />
      <directionalLight position={[5, 5, 5]} intensity={0.8} />
      <WaveMesh accentColor={accentColor} />
    </Canvas>
  )
}
