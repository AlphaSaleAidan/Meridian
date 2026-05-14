import React, { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { MeshDistortMaterial } from '@react-three/drei'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

function MorphBlob({ accentColor }: { accentColor: string }) {
  const ref = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.x = clock.getElapsedTime() * 0.1
    ref.current.rotation.y = clock.getElapsedTime() * 0.15
  })

  return (
    <mesh ref={ref} scale={2}>
      <sphereGeometry args={[1, 64, 64]} />
      <MeshDistortMaterial
        color={accentColor}
        emissive={accentColor}
        emissiveIntensity={0.5}
        distort={0.4}
        speed={2}
        roughness={0.3}
        metalness={0.2}
      />
    </mesh>
  )
}

export default function MorphingBlobScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 5], fov: 55 }}>
      <color attach="background" args={[primaryColor]} />
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 5, 5]} intensity={1} />
      <pointLight position={[-3, 2, 4]} intensity={0.6} color={accentColor} />
      <MorphBlob accentColor={accentColor} />
    </Canvas>
  )
}
