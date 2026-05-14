import React, { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Environment } from '@react-three/drei'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

function MetalKnot({ accentColor }: { accentColor: string }) {
  const ref = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.x = clock.getElapsedTime() * 0.15
    ref.current.rotation.y = clock.getElapsedTime() * 0.2
  })

  return (
    <mesh ref={ref} scale={1.2}>
      <torusKnotGeometry args={[1, 0.35, 128, 32]} />
      <meshPhysicalMaterial
        color={accentColor}
        metalness={1.0}
        roughness={0.05}
        clearcoat={1.0}
        clearcoatRoughness={0.05}
        reflectivity={1.0}
      />
    </mesh>
  )
}

export default function LiquidMetalScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 5], fov: 50 }}>
      <color attach="background" args={[primaryColor]} />
      <ambientLight intensity={0.3} />
      <directionalLight position={[5, 5, 5]} intensity={1.5} />
      <directionalLight position={[-5, -3, 3]} intensity={0.5} color={accentColor} />
      <Environment preset="city" />
      <MetalKnot accentColor={accentColor} />
    </Canvas>
  )
}
