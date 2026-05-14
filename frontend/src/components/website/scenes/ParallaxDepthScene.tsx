import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

function ParallaxLayers({ accentColor }: { accentColor: string }) {
  const layers = useMemo(() => [
    { z: -2, opacity: 0.6, scale: 1.0 },
    { z: -4, opacity: 0.4, scale: 1.2 },
    { z: -6, opacity: 0.25, scale: 1.4 },
    { z: -8, opacity: 0.12, scale: 1.6 },
  ], [])
  const groupRef = useRef<THREE.Group>(null)
  const { pointer } = useThree()

  useFrame(() => {
    if (!groupRef.current) return
    groupRef.current.children.forEach((child, i) => {
      const depth = (i + 1) * 0.3
      child.position.x = pointer.x * depth
      child.position.y = pointer.y * depth * 0.6
    })
  })

  return (
    <group ref={groupRef}>
      {layers.map((layer, i) => (
        <group key={i} position={[0, 0, layer.z]}>
          <gridHelper
            args={[12 * layer.scale, 12, accentColor, accentColor]}
            rotation={[Math.PI / 2, 0, 0]}
            material-transparent
            material-opacity={layer.opacity}
          />
          {[-4, -2, 0, 2, 4].map((x) => (
            <mesh key={x} position={[x * layer.scale, 0, 0]}>
              <boxGeometry args={[0.02, 6 * layer.scale, 0.02]} />
              <meshBasicMaterial color={accentColor} transparent opacity={layer.opacity * 0.6} />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  )
}

export default function ParallaxDepthScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 3], fov: 60 }}>
      <color attach="background" args={[primaryColor]} />
      <ParallaxLayers accentColor={accentColor} />
    </Canvas>
  )
}
