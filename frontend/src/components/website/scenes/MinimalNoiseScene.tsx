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
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`

const fragmentShader = `
  uniform float uTime;
  uniform vec3 uColor;

  varying vec2 vUv;

  float random(vec2 st, float seed) {
    return fract(sin(dot(st, vec2(12.9898, 78.233)) * 43758.5453 + seed));
  }

  void main() {
    float noise = random(vUv * 500.0, uTime) * 0.06;
    vec3 col = uColor + vec3(noise - 0.03);
    gl_FragColor = vec4(col, 1.0);
  }
`

function NoiseQuad({ primaryColor }: { primaryColor: string }) {
  const matRef = useRef<THREE.ShaderMaterial>(null)
  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uColor: { value: new THREE.Color(primaryColor) },
  }), [primaryColor])

  useFrame(({ clock }) => {
    if (matRef.current) {
      matRef.current.uniforms.uTime.value = clock.getElapsedTime()
    }
  })

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={matRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
      />
    </mesh>
  )
}

export default function MinimalNoiseScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} camera={{ position: [0, 0, 1], fov: 60 }}>
      <NoiseQuad primaryColor={primaryColor} />
    </Canvas>
  )
}
