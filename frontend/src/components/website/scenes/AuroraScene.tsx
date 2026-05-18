import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

const auroraVertex = `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position, 1.0); }`

const auroraFragment = `
uniform float uTime;
uniform vec3 uColor1;
uniform vec3 uColor2;
varying vec2 vUv;

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1,0)), f.x),
             mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), f.x), f.y);
}

float fbm(vec2 p) {
  float v = 0.0, a = 0.5;
  mat2 m = mat2(0.8, 0.6, -0.6, 0.8);
  for (int i = 0; i < 6; i++) {
    v += a * noise(p);
    p = m * p * 2.0;
    a *= 0.5;
  }
  return v;
}

void main() {
  vec2 uv = vUv;
  float t = uTime * 0.15;

  float n1 = fbm(vec2(uv.x * 3.0 + t, uv.y * 1.5 + t * 0.3));
  float n2 = fbm(vec2(uv.x * 5.0 - t * 0.5, uv.y * 2.0 + t * 0.2));
  float n3 = fbm(vec2(uv.x * 2.0 + n1 * 2.0 + t * 0.1, uv.y * 4.0 + n2));

  float curtain = smoothstep(0.2, 0.8, uv.y);
  curtain *= smoothstep(0.0, 0.3, uv.y);
  float aurora = (n3 * 0.6 + n1 * 0.4) * curtain;
  aurora = pow(aurora, 1.5) * 2.0;

  vec3 col1 = uColor1;
  vec3 col2 = uColor2;
  vec3 col3 = mix(col1, col2, 0.5) * 1.5;

  vec3 color = mix(col1, col2, n1) * aurora;
  color += col3 * pow(aurora, 3.0) * 0.5;

  float stars = step(0.998, hash(floor(uv * 500.0)));
  float twinkle = sin(uTime * 3.0 + hash(floor(uv * 500.0)) * 100.0) * 0.5 + 0.5;
  color += stars * twinkle * 0.8;

  vec3 sky = mix(vec3(0.01, 0.01, 0.03), col1 * 0.1, smoothstep(0.0, 0.5, uv.y));
  color += sky;

  gl_FragColor = vec4(color, 1.0);
}
`

function AuroraPlane({ primaryColor, accentColor }: SceneProps) {
  const ref = useRef<THREE.ShaderMaterial>(null)
  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uColor1: { value: new THREE.Color(primaryColor) },
    uColor2: { value: new THREE.Color(accentColor) },
  }), [primaryColor, accentColor])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.uniforms.uTime.value = clock.getElapsedTime()
  })

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial ref={ref} vertexShader={auroraVertex} fragmentShader={auroraFragment} uniforms={uniforms} />
    </mesh>
  )
}

function FloatingIceShard({ position, scale, color, speed }: {
  position: [number, number, number]; scale: number; color: string; speed: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.x = clock.getElapsedTime() * speed * 0.3
    ref.current.rotation.y = clock.getElapsedTime() * speed * 0.2
  })
  return (
    <Float speed={speed * 1.5} rotationIntensity={0.2} floatIntensity={0.5}>
      <mesh ref={ref} position={position} scale={scale}>
        <octahedronGeometry args={[1, 0]} />
        <meshPhysicalMaterial
          color={color} metalness={0.1} roughness={0.05}
          transmission={0.9} thickness={0.3} ior={1.5}
          iridescence={1} iridescenceIOR={1.3}
          iridescenceThicknessRange={[100, 400]}
          transparent opacity={0.7}
        />
      </mesh>
    </Float>
  )
}

function AuroraContent({ primaryColor, accentColor }: SceneProps) {
  return (
    <>
      <AuroraPlane primaryColor={primaryColor} accentColor={accentColor} />
      <FloatingIceShard position={[-2, -0.5, 2]} scale={0.08} color={accentColor} speed={0.6} />
      <FloatingIceShard position={[2.5, 0.3, 2]} scale={0.06} color={primaryColor} speed={0.8} />
      <FloatingIceShard position={[0.5, -0.8, 2]} scale={0.05} color={accentColor} speed={1.0} />
      <ambientLight intensity={0.5} />
      <pointLight position={[2, 2, 3]} intensity={1} color={accentColor} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.2} luminanceSmoothing={0.9} intensity={1.5} />
      </EffectComposer>
    </>
  )
}

export default function AuroraScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 1] }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.5 }}
    >
      <AuroraContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
