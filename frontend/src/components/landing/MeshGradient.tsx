import { useRef, useMemo, useState, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

/**
 * Animated WebGL mesh gradient background.
 * Slow-moving, low-contrast, atmospheric — like Vercel/Linear hero.
 */

const vertexShader = `
  varying vec2 vUv;
  varying float vDistortion;
  uniform float uTime;

  // simplex-ish noise
  vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 permute(vec4 x) { return mod289(((x * 34.0) + 1.0) * x); }
  vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

  float snoise(vec3 v) {
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;
    i = mod289(i);
    vec4 p = permute(permute(permute(
      i.z + vec4(0.0, i1.z, i2.z, 1.0))
      + i.y + vec4(0.0, i1.y, i2.y, 1.0))
      + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 0.142857142857;
    vec3 ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0) * 2.0 + 1.0;
    vec4 s1 = floor(b1) * 2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
  }

  void main() {
    vUv = uv;
    float noise = snoise(vec3(position.x * 0.8, position.y * 0.8, uTime * 0.15));
    vDistortion = noise;
    vec3 pos = position;
    pos.z += noise * 0.35;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`

const fragmentShader = `
  varying vec2 vUv;
  varying float vDistortion;
  uniform float uTime;
  uniform vec3 uColor1;
  uniform vec3 uColor2;
  uniform vec3 uColor3;

  void main() {
    float mixVal = vDistortion * 0.5 + 0.5;
    vec3 color = mix(uColor1, uColor2, smoothstep(0.0, 0.5, mixVal));
    color = mix(color, uColor3, smoothstep(0.5, 1.0, mixVal));

    // Add subtle vignette
    float dist = length(vUv - 0.5) * 1.4;
    float vignette = 1.0 - smoothstep(0.4, 1.2, dist);
    color *= vignette * 0.7 + 0.3;

    gl_FragColor = vec4(color, 0.6);
  }
`

function MeshGradientScene() {
  const meshRef = useRef<THREE.Mesh>(null)

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uColor1: { value: new THREE.Color('#0A0A0B') },
      uColor2: { value: new THREE.Color('#0D2A4A') },
      uColor3: { value: new THREE.Color('#0B3048') },
    }),
    []
  )

  useFrame(({ clock }) => {
    uniforms.uTime.value = clock.elapsedTime
  })

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 3, 0, 0]} position={[0, 0, -1]}>
      <planeGeometry args={[8, 8, 64, 64]} />
      <shaderMaterial
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
        transparent
        depthWrite={false}
      />
    </mesh>
  )
}

export default function MeshGradient() {
  const [contextLost, setContextLost] = useState(false)

  const handleCreated = useCallback(({ gl }: { gl: THREE.WebGLRenderer }) => {
    const canvas = gl.domElement
    canvas.addEventListener('webglcontextlost', (e) => {
      e.preventDefault()
      setContextLost(true)
      console.warn('[MeshGradient] WebGL context lost — hiding 3D background')
    })
    canvas.addEventListener('webglcontextrestored', () => {
      setContextLost(false)
      console.info('[MeshGradient] WebGL context restored')
    })
  }, [])

  // Graceful fallback when WebGL context is lost
  if (contextLost) {
    return (
      <div
        className="absolute inset-0 overflow-hidden"
        style={{
          background: 'radial-gradient(ellipse at 50% 40%, #0D2A4A 0%, #0A0A0B 70%)',
          filter: 'blur(40px)',
          opacity: 0.6,
        }}
      />
    )
  }

  return (
    <div className="absolute inset-0 overflow-hidden" style={{ filter: 'blur(40px)' }}>
      <Canvas
        camera={{ position: [0, 0, 3], fov: 50 }}
        dpr={[1, 1.5]}
        gl={{ alpha: true, antialias: false, powerPreference: 'low-power' }}
        style={{ background: 'transparent' }}
        onCreated={handleCreated}
      >
        <MeshGradientScene />
      </Canvas>
    </div>
  )
}
