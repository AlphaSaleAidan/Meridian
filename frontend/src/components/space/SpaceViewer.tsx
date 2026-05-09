import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera, Grid, Html } from '@react-three/drei'
import * as THREE from 'three'

interface SpacePoint {
  x: number
  y: number
  z: number
  category: 'floor' | 'wall' | 'fixture' | 'product' | 'counter' | 'entrance'
}

interface HotZone {
  id: string
  label: string
  position: [number, number, number]
  radius: number
  intensity: number
  color: string
}

function generateDemoScan(): { points: SpacePoint[]; hotZones: HotZone[] } {
  const points: SpacePoint[] = []
  const rng = (min: number, max: number) => min + Math.random() * (max - min)

  // Floor plane
  for (let i = 0; i < 800; i++) {
    points.push({ x: rng(-6, 6), y: 0, z: rng(-4, 4), category: 'floor' })
  }

  // Walls
  for (let i = 0; i < 200; i++) {
    const h = rng(0, 3)
    points.push({ x: -6, y: h, z: rng(-4, 4), category: 'wall' })
    points.push({ x: 6, y: h, z: rng(-4, 4), category: 'wall' })
    points.push({ x: rng(-6, 6), y: h, z: -4, category: 'wall' })
    points.push({ x: rng(-6, 6), y: h, z: 4, category: 'wall' })
  }

  // Counter (front of store)
  for (let i = 0; i < 150; i++) {
    points.push({ x: rng(2, 5), y: rng(0, 1.1), z: rng(-1.5, -0.5), category: 'counter' })
  }

  // Product shelves (left side)
  for (let shelf = 0; shelf < 3; shelf++) {
    for (let i = 0; i < 100; i++) {
      points.push({
        x: rng(-5, -3),
        y: rng(0.3, 2.5),
        z: rng(-3 + shelf * 2, -1.5 + shelf * 2),
        category: 'fixture',
      })
    }
  }

  // Display products (center)
  for (let i = 0; i < 80; i++) {
    points.push({ x: rng(-1, 1), y: rng(0.5, 1.8), z: rng(-2, 2), category: 'product' })
  }

  // Entrance
  for (let i = 0; i < 40; i++) {
    points.push({ x: rng(-1, 1), y: rng(0, 2.8), z: rng(3.5, 4), category: 'entrance' })
  }

  const hotZones: HotZone[] = [
    { id: 'counter', label: 'POS Counter', position: [3.5, 0.5, -1], radius: 1.5, intensity: 0.95, color: '#17C5B0' },
    { id: 'entrance', label: 'Entrance', position: [0, 0, 3.8], radius: 2, intensity: 0.7, color: '#1A8FD6' },
    { id: 'display', label: 'Feature Display', position: [0, 0.8, 0], radius: 1.8, intensity: 0.85, color: '#7C5CFF' },
    { id: 'shelf-a', label: 'High-Value Shelf', position: [-4, 1, -2], radius: 1.2, intensity: 0.6, color: '#FBBF24' },
  ]

  return { points, hotZones }
}

const categoryColors: Record<string, string> = {
  floor: '#1F1F23',
  wall: '#3A3A42',
  fixture: '#1A8FD6',
  product: '#17C5B0',
  counter: '#7C5CFF',
  entrance: '#FBBF24',
}

function PointCloud({ points }: { points: SpacePoint[] }) {
  const meshRef = useRef<THREE.InstancedMesh>(null!)
  const dummy = useMemo(() => new THREE.Object3D(), [])

  useMemo(() => {
    if (!meshRef.current) return
    const mesh = meshRef.current
    points.forEach((p, i) => {
      dummy.position.set(p.x, p.y, p.z)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
      mesh.setColorAt(i, new THREE.Color(categoryColors[p.category] || '#17C5B0'))
    })
    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  }, [points, dummy])

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, points.length]}>
      <sphereGeometry args={[0.03, 6, 6]} />
      <meshBasicMaterial />
    </instancedMesh>
  )
}

function HotZoneRing({ zone }: { zone: HotZone }) {
  const ref = useRef<THREE.Mesh>(null!)

  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.z += delta * 0.3
    }
  })

  return (
    <group position={zone.position}>
      <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <ringGeometry args={[zone.radius * 0.8, zone.radius, 48]} />
        <meshBasicMaterial color={zone.color} transparent opacity={zone.intensity * 0.15} side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <circleGeometry args={[zone.radius * 0.8, 48]} />
        <meshBasicMaterial color={zone.color} transparent opacity={zone.intensity * 0.06} side={THREE.DoubleSide} />
      </mesh>
      <Html position={[0, 0.3, 0]} center distanceFactor={8} zIndexRange={[1, 0]}>
        <div className="px-2 py-1 rounded-md bg-[#0A0A0B]/90 border border-[#1F1F23] whitespace-nowrap pointer-events-none select-none">
          <p className="text-[10px] font-medium text-[#F5F5F7]">{zone.label}</p>
          <p className="text-[8px] font-mono" style={{ color: zone.color }}>{Math.round(zone.intensity * 100)}% traffic</p>
        </div>
      </Html>
    </group>
  )
}

function SweepLine() {
  const ref = useRef<THREE.Group>(null!)

  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.8
    }
  })

  return (
    <group ref={ref} position={[0, 0.05, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[0.02, 12]} />
        <meshBasicMaterial color="#17C5B0" transparent opacity={0.6} side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, Math.PI / 12]}>
        <planeGeometry args={[0.6, 12]} />
        <meshBasicMaterial color="#17C5B0" transparent opacity={0.05} side={THREE.DoubleSide} />
      </mesh>
    </group>
  )
}

interface SpaceViewerProps {
  showHotZones?: boolean
  showSweep?: boolean
  className?: string
}

export default function SpaceViewer({
  showHotZones = true,
  showSweep = true,
  className = '',
}: SpaceViewerProps) {
  const { points, hotZones } = useMemo(() => generateDemoScan(), [])

  return (
    <div className={`relative rounded-xl overflow-hidden bg-[#0A0A0B] border border-[#1F1F23] isolate ${className}`}>
      <Canvas
        style={{ height: '100%', width: '100%' }}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ gl }) => gl.setClearColor('#0A0A0B')}
      >
        <PerspectiveCamera makeDefault position={[8, 6, 8]} fov={50} />
        <OrbitControls
          enableDamping
          dampingFactor={0.1}
          minDistance={3}
          maxDistance={20}
          maxPolarAngle={Math.PI / 2.1}
        />
        <ambientLight intensity={0.3} />
        <Grid
          args={[20, 20]}
          cellSize={1}
          cellColor="#1F1F23"
          sectionSize={5}
          sectionColor="#2A2A30"
          fadeDistance={25}
          position={[0, -0.01, 0]}
        />
        <PointCloud points={points} />
        {showHotZones && hotZones.map(z => <HotZoneRing key={z.id} zone={z} />)}
        {showSweep && <SweepLine />}
      </Canvas>

      {/* Legend overlay */}
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-2">
        {Object.entries(categoryColors).map(([cat, color]) => (
          <div key={cat} className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-[#0A0A0B]/80 border border-[#1F1F23]">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-[9px] text-[#A1A1A8] capitalize">{cat}</span>
          </div>
        ))}
      </div>

      {/* Scan info */}
      <div className="absolute top-3 right-3 px-3 py-2 rounded-lg bg-[#0A0A0B]/80 border border-[#1F1F23]">
        <p className="text-[10px] font-mono text-[#17C5B0]">{points.length.toLocaleString()} points</p>
        <p className="text-[9px] text-[#A1A1A8]/40">{hotZones.length} zones detected</p>
      </div>
    </div>
  )
}
