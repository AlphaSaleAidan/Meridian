import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

const gradientFragment = `
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
  for (int i = 0; i < 7; i++) {
    v += a * noise(p);
    p = m * p * 2.0;
    a *= 0.5;
  }
  return v;
}

void main() {
  vec2 uv = vUv;
  float t = uTime * 0.1;

  float warp1 = fbm(uv * 3.0 + t);
  float warp2 = fbm(uv * 3.0 + warp1 * 2.0 + t * 0.5);
  float warp3 = fbm(uv * 3.0 + warp2 * 2.0 + t * 0.3);

  vec3 col1 = uColor1;
  vec3 col2 = uColor2;
  vec3 col3 = mix(col1, col2, 0.5) * 1.3;
  vec3 dark = col1 * 0.15;

  vec3 color = mix(col1, col2, warp3);
  color = mix(color, col3, warp1 * warp2);
  color = mix(dark, color, smoothstep(0.2, 0.8, warp3));

  float highlight = pow(warp3, 3.0) * 0.5;
  color += highlight * col2;

  float grain = (hash(uv * 1000.0 + t) - 0.5) * 0.03;
  color += grain;

  gl_FragColor = vec4(color, 1.0);
}
`

const gradientVertex = `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position, 1.0); }`

function GradientPlane({ primaryColor, accentColor }: SceneProps) {
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
      <shaderMaterial ref={ref} vertexShader={gradientVertex} fragmentShader={gradientFragment} uniforms={uniforms} />
    </mesh>
  )
}

function PrismaticGem({ position, scale, color, speed }: {
  position: [number, number, number]; scale: number; color: string; speed: number
}) {
  const ref = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    ref.current.rotation.x = clock.getElapsedTime() * speed * 0.5
    ref.current.rotation.y = clock.getElapsedTime() * speed * 0.7
  })
  return (
    <Float speed={speed} rotationIntensity={0.15} floatIntensity={0.4}>
      <mesh ref={ref} position={position} scale={scale}>
        <dodecahedronGeometry args={[1, 0]} />
        <meshPhysicalMaterial
          color={color} metalness={0.1} roughness={0.05}
          clearcoat={1} clearcoatRoughness={0.1}
          sheen={1} sheenRoughness={0.1} sheenColor={new THREE.Color(color)}
          iridescence={1} iridescenceIOR={1.3}
          iridescenceThicknessRange={[100, 400]}
          envMapIntensity={1.5}
        />
      </mesh>
    </Float>
  )
}

function GradientContent({ primaryColor, accentColor }: SceneProps) {
  return (
    <>
      <GradientPlane primaryColor={primaryColor} accentColor={accentColor} />
      <PrismaticGem position={[-1.5, -0.6, 2]} scale={0.06} color={accentColor} speed={0.7} />
      <PrismaticGem position={[1.8, 0.4, 2]} scale={0.05} color={primaryColor} speed={0.9} />
      <PrismaticGem position={[0.3, 0.8, 2]} scale={0.04} color={accentColor} speed={1.1} />
      <ambientLight intensity={0.5} />
      <pointLight position={[2, 2, 3]} intensity={1} color={accentColor} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.4} luminanceSmoothing={0.9} intensity={0.8} />
      </EffectComposer>
    </>
  )
}

export default function GradientMeshScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 1] }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.3 }}
    >
      <GradientContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
