import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

const vertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`

const fragmentShader = `
  uniform float uTime;
  uniform float uOffset;
  varying vec2 vUv;

  void main() {
    float r = sin(vUv.x * 6.2832 + uTime * 1.5 + uOffset) * 0.5 + 0.5;
    float g = sin(vUv.x * 6.2832 + uTime * 1.5 + uOffset + 2.094) * 0.5 + 0.5;
    float b = sin(vUv.x * 6.2832 + uTime * 1.5 + uOffset + 4.189) * 0.5 + 0.5;
    float scanline = sin(vUv.y * 80.0 + uTime * 5.0) * 0.05 + 0.95;
    gl_FragColor = vec4(r * scanline, g * scanline, b * scanline, 0.3);
  }
`

interface HoloPanel {
  x: number; y: number; z: number
  rx: number; ry: number
  w: number; h: number; offset: number
}

function HoloPanels() {
  const groupRef = useRef<THREE.Group>(null)
  const matsRef = useRef<THREE.ShaderMaterial[]>([])

  const panels = useMemo<HoloPanel[]>(() =>
    Array.from({ length: 7 }, () => ({
      x: (Math.random() - 0.5) * 6,
      y: (Math.random() - 0.5) * 4,
      z: (Math.random() - 0.5) * 3 - 1,
      rx: (Math.random() - 0.5) * 0.6,
      ry: (Math.random() - 0.5) * 0.8,
      w: 1 + Math.random() * 2,
      h: 1 + Math.random() * 2,
      offset: Math.random() * Math.PI * 2,
    }))
  , [])

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    matsRef.current.forEach((mat) => {
      if (mat) mat.uniforms.uTime.value = t
    })
    if (groupRef.current) {
      groupRef.current.children.forEach((child, i) => {
        const p = panels[i]
        child.rotation.y = p.ry + Math.sin(t * 0.2 + p.offset) * 0.1
      })
    }
  })

  return (
    <group ref={groupRef}>
      {panels.map((p, i) => (
        <mesh key={i} position={[p.x, p.y, p.z]} rotation={[p.rx, p.ry, 0]}>
          <planeGeometry args={[p.w, p.h]} />
          <shaderMaterial
            ref={(el) => { if (el) matsRef.current[i] = el }}
            vertexShader={vertexShader}
            fragmentShader={fragmentShader}
            uniforms={{
              uTime: { value: 0 },
              uOffset: { value: p.offset },
            }}
            transparent
            side={THREE.DoubleSide}
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      ))}
    </group>
  )
}

export default function HolographicScene({ primaryColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 5], fov: 55 }}>
      <color attach="background" args={[primaryColor]} />
      <HoloPanels />
    </Canvas>
  )
}
