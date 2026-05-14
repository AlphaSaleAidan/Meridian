import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface SceneProps {
  primaryColor: string
  accentColor: string
}

function AuroraBand({ color1, color2, yOffset }: { color1: THREE.Color; color2: THREE.Color; yOffset: number }) {
  const ref = useRef<THREE.Points>(null)
  const count = 700
  const { positions, colors } = useMemo(() => {
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const i3 = i * 3
      pos[i3] = (Math.random() - 0.5) * 12
      pos[i3 + 1] = (Math.random() - 0.5) * 0.6 + yOffset
      pos[i3 + 2] = (Math.random() - 0.5) * 3 - 2
      const t = i / count
      col[i3] = color1.r + (color2.r - color1.r) * t
      col[i3 + 1] = color1.g + (color2.g - color1.g) * t
      col[i3 + 2] = color1.b + (color2.b - color1.b) * t
    }
    return { positions: pos, colors: col }
  }, [color1, color2, yOffset])

  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime()
    const posArr = ref.current.geometry.attributes.position.array as Float32Array
    for (let i = 0; i < count; i++) {
      const i3 = i * 3
      const origX = (i / count - 0.5) * 12
      posArr[i3] = origX + Math.sin(t * 0.2 + i * 0.01) * 0.3
      posArr[i3 + 1] = yOffset + Math.sin(origX * 0.5 + t * 0.6) * 0.8 + Math.cos(t * 0.3 + i * 0.02) * 0.3
    }
    ref.current.geometry.attributes.position.needsUpdate = true
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={count} itemSize={3} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} count={count} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.08} vertexColors sizeAttenuation transparent opacity={0.7} blending={THREE.AdditiveBlending} />
    </points>
  )
}

function AuroraContent({ primaryColor, accentColor }: SceneProps) {
  const c1 = useMemo(() => new THREE.Color(primaryColor), [primaryColor])
  const c2 = useMemo(() => new THREE.Color(accentColor), [accentColor])
  return (
    <>
      <color attach="background" args={[primaryColor]} />
      <AuroraBand color1={c1} color2={c2} yOffset={1.0} />
      <AuroraBand color1={c2} color2={c1} yOffset={0.2} />
      <AuroraBand color1={c1} color2={c2} yOffset={-0.6} />
    </>
  )
}

export default function AuroraScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 5], fov: 60 }}>
      <AuroraContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
