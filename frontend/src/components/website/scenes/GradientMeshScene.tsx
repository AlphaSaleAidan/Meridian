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
  uniform vec3 uColor1;
  uniform vec3 uColor2;
  varying vec2 vUv;

  void main() {
    float t1 = sin(vUv.x * 3.14159 + uTime * 0.5) * 0.5 + 0.5;
    float t2 = cos(vUv.y * 3.14159 + uTime * 0.3) * 0.5 + 0.5;
    float t3 = sin((vUv.x + vUv.y) * 2.0 + uTime * 0.4) * 0.5 + 0.5;
    float t4 = cos((vUv.x - vUv.y) * 2.5 + uTime * 0.6) * 0.5 + 0.5;
    float mix1 = t1 * 0.3 + t2 * 0.3 + t3 * 0.2 + t4 * 0.2;
    vec3 col = mix(uColor1, uColor2, mix1);
    gl_FragColor = vec4(col, 1.0);
  }
`

function GradientPlane({ primaryColor, accentColor }: SceneProps) {
  const matRef = useRef<THREE.ShaderMaterial>(null)
  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uColor1: { value: new THREE.Color(primaryColor) },
    uColor2: { value: new THREE.Color(accentColor) },
  }), [primaryColor, accentColor])

  useFrame(({ clock }) => {
    if (matRef.current) {
      matRef.current.uniforms.uTime.value = clock.getElapsedTime()
    }
  })

  return (
    <mesh>
      <planeGeometry args={[12, 8]} />
      <shaderMaterial
        ref={matRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
      />
    </mesh>
  )
}

export default function GradientMeshScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 5], fov: 50 }}>
      <GradientPlane primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
