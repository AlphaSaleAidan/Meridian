import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

interface SceneProps { primaryColor: string; accentColor: string }

const gridFragment = `
uniform float uTime;
uniform vec3 uColor1;
uniform vec3 uColor2;
varying vec2 vUv;

void main() {
  vec2 uv = vUv;
  float t = uTime * 0.3;

  float perspective = pow(1.0 - uv.y, 2.0);
  vec2 grid = vec2((uv.x - 0.5) * 8.0 / (uv.y + 0.2), 1.0 / (uv.y + 0.05) - t * 3.0);

  float lineX = smoothstep(0.02, 0.0, abs(fract(grid.x) - 0.5) - 0.48) * perspective;
  float lineY = smoothstep(0.02, 0.0, abs(fract(grid.y) - 0.5) - 0.48) * perspective;
  float gridLines = max(lineX, lineY);
  float glow = gridLines * (1.0 + sin(grid.y * 2.0 + uTime) * 0.3);

  vec3 gridCol = mix(uColor1, uColor2, sin(grid.y * 0.5 + uTime) * 0.5 + 0.5);
  vec3 color = gridCol * glow * 2.0;

  float horizon = smoothstep(0.48, 0.52, uv.y);
  float sunY = (uv.y - 0.65);
  float sunX = (uv.x - 0.5);
  float sun = smoothstep(0.12, 0.0, length(vec2(sunX, sunY * 1.5)));
  float sunLines = step(0.0, sin(sunY * 80.0 + uTime)) * 0.3;
  vec3 sunCol = mix(uColor2, uColor1, sunY * 4.0 + 0.5);
  color += sun * sunCol * (1.0 - sunLines) * 2.0;

  float sunGlow = smoothstep(0.4, 0.0, length(vec2(sunX, sunY * 1.2))) * 0.15;
  color += sunGlow * uColor2;

  vec3 sky = mix(uColor1 * 0.15, vec3(0.01, 0.0, 0.03), smoothstep(0.5, 1.0, uv.y));
  color = mix(color, sky, horizon * (1.0 - sun));

  float scanline = sin(uv.y * 400.0 + uTime * 2.0) * 0.02 + 0.98;
  color *= scanline;

  float chromatic = sin(uv.y * 200.0) * 0.01;
  color.r += chromatic;
  color.b -= chromatic;

  gl_FragColor = vec4(color, 1.0);
}
`

const gridVertex = `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position, 1.0); }`

function NeonGrid({ primaryColor, accentColor }: SceneProps) {
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
      <shaderMaterial ref={ref} vertexShader={gridVertex} fragmentShader={gridFragment} uniforms={uniforms} />
    </mesh>
  )
}

function NeonOrb({ position, color, scale }: {
  position: [number, number, number]; color: string; scale: number
}) {
  return (
    <Float speed={2} floatIntensity={0.8}>
      <mesh position={position} scale={scale}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshPhysicalMaterial
          color={color} emissive={color} emissiveIntensity={2}
          metalness={0.9} roughness={0.1}
          clearcoat={1} clearcoatRoughness={0}
        />
      </mesh>
    </Float>
  )
}

function NeonContent({ primaryColor, accentColor }: SceneProps) {
  return (
    <>
      <NeonGrid primaryColor={primaryColor} accentColor={accentColor} />
      <NeonOrb position={[-1.5, -0.3, 2]} color={accentColor} scale={0.04} />
      <NeonOrb position={[1.2, -0.5, 2]} color={primaryColor} scale={0.03} />
      <NeonOrb position={[0.5, -0.7, 2]} color={accentColor} scale={0.025} />
      <ambientLight intensity={0.3} />
      <EffectComposer>
        <Bloom luminanceThreshold={0.15} luminanceSmoothing={0.9} intensity={2.0} />
      </EffectComposer>
    </>
  )
}

export default function NeonGridScene({ primaryColor, accentColor }: SceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      camera={{ position: [0, 0, 1] }} dpr={[1, 1.5]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.5 }}
    >
      <NeonContent primaryColor={primaryColor} accentColor={accentColor} />
    </Canvas>
  )
}
