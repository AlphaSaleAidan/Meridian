import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

function GridContent({ primaryColor, accentColor }: SceneProps) {
  const groupRef = useRef<THREE.Group>(null)
  const linesRef = useRef<THREE.Group>(null)

  const lines = useMemo(() => {
    const items: { x: number; height: number; speed: number }[] = []
    for (let i = 0; i < 20; i++) {
      items.push({
        x: (Math.random() - 0.5) * 20,
        height: 1 + Math.random() * 3,
        speed: 0.3 + Math.random() * 0.7,
      })
    }
    return items
  }, [])

  useFrame(({ clock }) => {
    if (!linesRef.current) return
    const t = clock.getElapsedTime()
    linesRef.current.children.forEach((child, i) => {
      const line = lines[i]
      child.position.z = ((line.speed * t * -2) % 30) + 15
      const mesh = child as THREE.Mesh
      if (mesh.material instanceof THREE.MeshBasicMaterial) {
        mesh.material.opacity = 0.3 + Math.sin(t * 2 + i) * 0.2
      }
    })
  })

  return (
    <>
      <color attach="background" args={[primaryColor]} />
      <fog attach="fog" args={[primaryColor, 5, 30]} />
      <group ref={groupRef} rotation={[-0.3, 0, 0]} position={[0, -1, 0]}>
        <gridHelper args={[60, 60, accentColor, accentColor]} position={[0, 0, -10]} material-opacity={0.3} material-transparent />
        <group ref={linesRef}>
          {lines.map((line, i) => (
            <mesh key={i} position={[line.x, line.height / 2, 0]}>
              <boxGeometry args={[0.03, line.height, 0.03]} />
              <meshBasicMaterial color={accentColor} transparent opacity={0.5} />
            </mesh>
          ))}
        </group>
      </group>
    </>
  )
}

export default function NeonGridScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 2, 8], fov: 70 }}>
      <GridContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
