import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial, RoundedBox, Environment } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

function HoloPanel({ position, rotation, scale, color, speed, offset }: {
  position: [number, number, number]; rotation: [number, number, number]
  scale: [number, number, number]; color: string; speed: number; offset: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    const t = clock.getElapsedTime() * speed + offset
    ref.current.rotation.y = rotation[1] + Math.sin(t * 0.4) * 0.08
    ref.current.rotation.x = rotation[0] + Math.cos(t * 0.3) * 0.04
  })
  return (
    <Float speed={speed * 1.2} rotationIntensity={0.08} floatIntensity={0.25}>
      <RoundedBox ref={ref} args={scale} radius={0.02} position={position} rotation={rotation}>
        <MeshTransmissionMaterial
          backside thickness={0.08} chromaticAberration={0.15}
          color={color} roughness={0.05} transmission={0.95} ior={1.3}
          distortion={0} distortionScale={0} anisotropy={0.8}
        />
      </RoundedBox>
    </Float>
  )
}

function ScanLine({ position, color }: { position: [number, number, number]; color: string }) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.position.y = position[1] + Math.sin(clock.getElapsedTime() * 0.8 + position[0]) * 2
  })
  return (
    <mesh ref={ref} position={position}>
      <planeGeometry args={[8, 0.003]} />
      <meshBasicMaterial color={color} transparent opacity={0.4} toneMapped={false} blending={THREE.AdditiveBlending} />
    </mesh>
  )
}

function HoloContent({ primaryColor, accentColor }: SceneProps) {
  const panels = useMemo(() => [
    { pos: [0, 0.2, 0] as [number, number, number], rot: [0.05, 0.15, 0] as [number, number, number], scale: [2.8, 2, 0.02] as [number, number, number], color: accentColor, speed: 0.5, offset: 0 },
    { pos: [-2, 0.8, -1] as [number, number, number], rot: [-0.05, -0.35, 0.05] as [number, number, number], scale: [1.6, 1.2, 0.015] as [number, number, number], color: primaryColor, speed: 0.7, offset: 1.5 },
    { pos: [2.2, -0.3, -0.8] as [number, number, number], rot: [0.03, 0.4, -0.03] as [number, number, number], scale: [1.4, 1.8, 0.015] as [number, number, number], color: accentColor, speed: 0.6, offset: 3 },
    { pos: [-1, -1.2, 0.3] as [number, number, number], rot: [0.1, -0.1, 0.08] as [number, number, number], scale: [2, 0.8, 0.01] as [number, number, number], color: primaryColor, speed: 0.8, offset: 4.5 },
    { pos: [1.5, 1.5, -1.5] as [number, number, number], rot: [-0.08, 0.25, 0.05] as [number, number, number], scale: [1.2, 1.5, 0.012] as [number, number, number], color: accentColor, speed: 0.55, offset: 2 },
  ], [primaryColor, accentColor])

  return (
    <>
      <color attach="background" args={['#020208']} />
      <fog attach="fog" args={['#020208', 4, 14]} />
      <ambientLight intensity={0.05} />
      <spotLight position={[3, 4, 3]} intensity={2.5} angle={0.5} penumbra={1} color={accentColor} />
      <spotLight position={[-4, -2, 4]} intensity={1.5} angle={0.6} penumbra={1} color={primaryColor} />
      <pointLight position={[0, 0, 3]} intensity={1} color="#ffffff" />
      <Environment preset="city" />
      {panels.map((p, i) => (
        <HoloPanel key={i} position={p.pos} rotation={p.rot} scale={p.scale} color={p.color} speed={p.speed} offset={p.offset} />
      ))}
      {[-1.5, -0.5, 0.5, 1.5].map((y, i) => (
        <ScanLine key={i} position={[0, y, 0.5]} color={accentColor} />
      ))}
      <EffectComposer>
        <Bloom luminanceThreshold={0.3} luminanceSmoothing={0.9} intensity={1.2} />
      </EffectComposer>
    </>
  )
}

export default function HolographicScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 5], fov: 50 }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.4 }}
    >
      <HoloContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
