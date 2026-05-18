import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

const vertexShader = `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position, 1.0); }`

const fragmentShader = `
uniform float uTime;
uniform vec3 uColor1;
uniform vec3 uColor2;
varying vec2 vUv;

float wave(vec2 p, float freq, float speed, float phase) {
  return sin(p.x * freq + uTime * speed + phase) * cos(p.y * freq * 0.7 + uTime * speed * 0.8 + phase * 1.3);
}

void main() {
  vec2 uv = vUv;
  float t = uTime * 0.2;
  float perspective = pow(1.0 - uv.y, 1.5);
  vec2 p = vec2((uv.x - 0.5) * 6.0 / (uv.y + 0.3), 1.0 / (uv.y + 0.1));
  float w = 0.0;
  w += wave(p, 1.0, 0.8, 0.0) * 0.5;
  w += wave(p, 2.3, 1.2, 1.7) * 0.25;
  w += wave(p, 4.1, 1.8, 3.2) * 0.125;
  w += wave(p, 7.0, 2.5, 5.1) * 0.0625;
  w += wave(p, 10.0, 3.0, 7.3) * 0.03;
  float surface = smoothstep(-0.02, 0.02, w * perspective * 0.3 + uv.y - 0.45);
  float foam = smoothstep(0.15, 0.2, abs(w)) * perspective * 0.6;
  float fresnel = pow(1.0 - abs(uv.y - 0.5) * 2.0, 2.0) * 0.3;
  vec3 deep = uColor1 * 0.3;
  vec3 mid = mix(uColor1, uColor2, 0.4);
  vec3 shallow = uColor2 * 0.8;
  vec3 waterCol = mix(deep, mid, smoothstep(0.0, 0.4, uv.y));
  waterCol = mix(waterCol, shallow, smoothstep(0.3, 0.7, uv.y + w * 0.1));
  waterCol += vec3(foam) * 0.5;
  waterCol += fresnel * uColor2;
  float caustic = sin(p.x * 3.0 + t * 4.0) * sin(p.y * 3.0 + t * 3.0);
  caustic = pow(max(caustic, 0.0), 4.0) * perspective * 0.15;
  waterCol += caustic * uColor2;

  float subsurface = sin(p.x * 1.5 + t * 2.0) * sin(p.y * 1.2 + t * 1.5);
  subsurface = pow(max(subsurface, 0.0), 3.0) * perspective * 0.1;
  waterCol += subsurface * mix(uColor1, uColor2, 0.7);

  vec3 sky = mix(uColor1 * 0.4, uColor1 * 0.15, uv.y);
  float starField = step(0.997, fract(sin(dot(floor(uv * 300.0), vec2(12.9898, 78.233))) * 43758.5453));
  sky += starField * 0.3 * step(0.6, uv.y);
  vec3 col = mix(sky, waterCol, surface);
  gl_FragColor = vec4(col, 1.0);
}
`

function WavePlane({ primaryColor, accentColor }: SceneProps) {
  const ref = useRef<THREE.ShaderMaterial>(null)
  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uColor1: { value: new THREE.Color(primaryColor) },
    uColor2: { value: new THREE.Color(accentColor) },
  }), [primaryColor, accentColor])

  useFrame(({ clock }) => { if (ref.current) ref.current.uniforms.uTime.value = clock.getElapsedTime() })

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial ref={ref} vertexShader={vertexShader} fragmentShader={fragmentShader} uniforms={uniforms} />
    </mesh>
  )
}

function FloatingLight({ position, color, scale }: {
  position: [number, number, number]; color: string; scale: number
}) {
  return (
    <Float speed={1.5} floatIntensity={0.6}>
      <mesh position={position} scale={scale}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
    </Float>
  )
}

function WavesContent({ primaryColor, accentColor }: SceneProps) {
  return (
    <>
      <WavePlane primaryColor={primaryColor} accentColor={accentColor} />
      <FloatingLight position={[-1.5, -0.3, 1]} color={accentColor} scale={0.03} />
      <FloatingLight position={[1.2, -0.5, 1]} color={primaryColor} scale={0.025} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.3} luminanceSmoothing={0.9} intensity={1.0} />
      </EffectComposer>
    </>
  )
}

export default function WavesScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 1] }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.4 }}
    >
      <WavesContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
