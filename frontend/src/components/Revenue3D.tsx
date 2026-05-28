import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text, RoundedBox } from '@react-three/drei'
import * as THREE from 'three'

interface BarData {
  label: string
  value: number
  color?: string
}

function Bar({ position, height, color, label, maxHeight }: {
  position: [number, number, number]
  height: number
  color: string
  label: string
  maxHeight: number
}) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const normalizedH = Math.max((height / maxHeight) * 3, 0.05)

  return (
    <group position={position}>
      <RoundedBox
        ref={meshRef}
        args={[0.6, normalizedH, 0.6]}
        radius={0.05}
        position={[0, normalizedH / 2, 0]}
      >
        <meshStandardMaterial color={color} metalness={0.1} roughness={0.4} />
      </RoundedBox>
      <Text
        position={[0, -0.3, 0]}
        fontSize={0.15}
        color="#A1A1A8"
        anchorX="center"
        rotation={[-Math.PI / 4, 0, 0]}
      >
        {label}
      </Text>
      <Text
        position={[0, normalizedH + 0.3, 0]}
        fontSize={0.14}
        color="#F5F5F7"
        anchorX="center"
      >
        ${(height / 100).toFixed(0)}
      </Text>
    </group>
  )
}

function BarChart({ data }: { data: BarData[] }) {
  const groupRef = useRef<THREE.Group>(null!)
  const maxVal = useMemo(() => Math.max(...data.map(d => d.value), 1), [data])

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.05
    }
  })

  return (
    <group ref={groupRef}>
      {data.map((d, i) => (
        <Bar
          key={d.label}
          position={[(i - data.length / 2) * 1, 0, 0]}
          height={d.value}
          color={d.color || '#0066FF'}
          label={d.label}
          maxHeight={maxVal}
        />
      ))}
      {/* Floor grid */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <planeGeometry args={[data.length * 1.2, 4]} />
        <meshStandardMaterial color="#111113" transparent opacity={0.5} />
      </mesh>
    </group>
  )
}

interface Revenue3DProps {
  data: BarData[]
  height?: number
}

export default function Revenue3D({ data, height = 300 }: Revenue3DProps) {
  if (!data || data.length === 0) return null

  return (
    <div style={{ height, width: '100%', borderRadius: 12, overflow: 'hidden', background: '#0A0A0B' }}>
      <Canvas
        camera={{ position: [0, 3, 6], fov: 50 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: false }}
      >
        <color attach="background" args={['#0A0A0B']} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 8, 5]} intensity={0.8} />
        <BarChart data={data} />
        <OrbitControls
          enableZoom={false}
          enablePan={false}
          maxPolarAngle={Math.PI / 2.2}
          minPolarAngle={Math.PI / 6}
        />
      </Canvas>
    </div>
  )
}
