import { useRef, useEffect, useState } from 'react'
import { Loader2, Maximize2, Minimize2 } from 'lucide-react'

interface SplatData {
  count: number
  positions: Float32Array
  scales: Float32Array
  colors: Uint8Array
  rotations: Float32Array
}

interface Props {
  url?: string
  file?: File | null
  className?: string
  onLoad?: (count: number) => void
}

function parseSplat(buf: ArrayBuffer): SplatData {
  const count = Math.floor(buf.byteLength / 32)
  if (count === 0) throw new Error('Empty or invalid .splat file')
  const f = new Float32Array(buf)
  const u = new Uint8Array(buf)
  const positions = new Float32Array(count * 3)
  const scales = new Float32Array(count * 3)
  const colors = new Uint8Array(count * 4)
  const rotations = new Float32Array(count * 4)
  for (let i = 0; i < count; i++) {
    const fi = i * 8, bi = i * 32
    positions[i * 3] = f[fi]; positions[i * 3 + 1] = f[fi + 1]; positions[i * 3 + 2] = f[fi + 2]
    scales[i * 3] = f[fi + 3]; scales[i * 3 + 1] = f[fi + 4]; scales[i * 3 + 2] = f[fi + 5]
    colors[i * 4] = u[bi + 24]; colors[i * 4 + 1] = u[bi + 25]
    colors[i * 4 + 2] = u[bi + 26]; colors[i * 4 + 3] = u[bi + 27]
    const w = u[bi + 28] - 128, x = u[bi + 29] - 128
    const y = u[bi + 30] - 128, z = u[bi + 31] - 128
    const n = Math.sqrt(w * w + x * x + y * y + z * z) || 1
    rotations[i * 4] = w / n; rotations[i * 4 + 1] = x / n
    rotations[i * 4 + 2] = y / n; rotations[i * 4 + 3] = z / n
  }
  return { count, positions, scales, colors, rotations }
}

const VERT = `#version 300 es
precision highp float;
in vec2 a_quad;
in vec3 a_center;
in vec3 a_scale;
in vec4 a_color;
in vec4 a_rot;
uniform mat4 u_view;
uniform mat4 u_proj;
uniform vec2 u_focal;
uniform vec2 u_viewport;
out vec4 vColor;
out vec2 vUV;

mat3 quat2mat(vec4 q) {
  float w = q.x, x = q.y, y = q.z, z = q.w;
  return mat3(
    1.0-2.0*(y*y+z*z), 2.0*(x*y-w*z), 2.0*(x*z+w*y),
    2.0*(x*y+w*z), 1.0-2.0*(x*x+z*z), 2.0*(y*z-w*x),
    2.0*(x*z-w*y), 2.0*(y*z+w*x), 1.0-2.0*(x*x+y*y)
  );
}

void main() {
  vec4 cam = u_view * vec4(a_center, 1.0);
  vec4 clip = u_proj * cam;
  float bnd = 1.2 * clip.w;
  if (clip.z < -clip.w || clip.x < -bnd || clip.x > bnd
      || clip.y < -bnd || clip.y > bnd) {
    gl_Position = vec4(0.0, 0.0, 2.0, 1.0); return;
  }
  mat3 R = quat2mat(a_rot);
  vec3 s = exp(a_scale);
  mat3 M = R * mat3(s.x,0,0, 0,s.y,0, 0,0,s.z);
  mat3 Sig = M * transpose(M);
  float z2 = cam.z * cam.z;
  mat3 J = mat3(
    u_focal.x/cam.z, 0.0, 0.0,
    0.0, u_focal.y/cam.z, 0.0,
    -(u_focal.x*cam.x)/z2, -(u_focal.y*cam.y)/z2, 0.0
  );
  mat3 W = transpose(mat3(u_view));
  mat3 T = W * J;
  mat3 cov = transpose(T) * Sig * T;
  float a = cov[0][0]+0.3, b = cov[0][1], d = cov[1][1]+0.3;
  float mid = 0.5*(a+d);
  float rad = length(vec2(0.5*(a-d), b));
  float l1 = mid+rad, l2 = max(mid-rad, 0.1);
  vec2 dv = normalize(vec2(b, l1-a));
  vec2 v1 = min(sqrt(2.0*l1), 1024.0) * dv;
  vec2 v2 = min(sqrt(2.0*l2), 1024.0) * vec2(dv.y, -dv.x);
  vColor = a_color;
  vUV = a_quad;
  vec2 ndc = clip.xy / clip.w;
  gl_Position = vec4(
    ndc + a_quad.x*v1/u_viewport*2.0 + a_quad.y*v2/u_viewport*2.0,
    clip.z/clip.w, 1.0
  );
}`

const FRAG = `#version 300 es
precision highp float;
in vec4 vColor;
in vec2 vUV;
out vec4 fragColor;
void main() {
  float p = -dot(vUV, vUV);
  if (p < -4.0) discard;
  float a = exp(p) * vColor.a;
  fragColor = vec4(vColor.rgb * a, a);
}`

const SORT_SRC = `self.onmessage=({data:{positions,viewRow,count}})=>{
const d=new Float32Array(count),ix=new Uint32Array(count);
for(let i=0;i<count;i++){
  d[i]=viewRow[0]*positions[i*3]+viewRow[1]*positions[i*3+1]+viewRow[2]*positions[i*3+2]+viewRow[3];
  ix[i]=i;
}
ix.sort((a,b)=>d[a]-d[b]);
self.postMessage(ix,[ix.buffer]);
};`

function createSortWorker(): Worker {
  return new Worker(URL.createObjectURL(new Blob([SORT_SRC], { type: 'application/javascript' })))
}

type V3 = [number, number, number]
const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
const cross = (a: V3, b: V3): V3 => [
  a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0],
]
const dot3 = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
const norm3 = (v: V3): V3 => {
  const l = Math.sqrt(dot3(v, v)) || 1; return [v[0] / l, v[1] / l, v[2] / l]
}

function lookAt(eye: V3, target: V3, up: V3): Float32Array {
  const z = norm3(sub(eye, target)), x = norm3(cross(up, z)), y = cross(z, x)
  return new Float32Array([
    x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0,
    -dot3(x, eye), -dot3(y, eye), -dot3(z, eye), 1,
  ])
}

function perspective(fov: number, aspect: number, near: number, far: number): Float32Array {
  const f = 1 / Math.tan(fov / 2), nf = 1 / (near - far)
  return new Float32Array([f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0])
}

function compileShader(gl: WebGL2RenderingContext, type: number, src: string) {
  const s = gl.createShader(type)!
  gl.shaderSource(s, src); gl.compileShader(s)
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || 'Shader error')
  return s
}

function linkProgram(gl: WebGL2RenderingContext, vs: string, fs: string) {
  const p = gl.createProgram()!
  gl.attachShader(p, compileShader(gl, gl.VERTEX_SHADER, vs))
  gl.attachShader(p, compileShader(gl, gl.FRAGMENT_SHADER, fs))
  gl.linkProgram(p)
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) || 'Link error')
  return p
}

function reorder(data: SplatData, idx: Uint32Array) {
  const n = idx.length
  const p = new Float32Array(n * 3), s = new Float32Array(n * 3)
  const c = new Uint8Array(n * 4), r = new Float32Array(n * 4)
  for (let i = 0; i < n; i++) {
    const j = idx[i]
    p[i*3] = data.positions[j*3]; p[i*3+1] = data.positions[j*3+1]; p[i*3+2] = data.positions[j*3+2]
    s[i*3] = data.scales[j*3]; s[i*3+1] = data.scales[j*3+1]; s[i*3+2] = data.scales[j*3+2]
    c[i*4] = data.colors[j*4]; c[i*4+1] = data.colors[j*4+1]; c[i*4+2] = data.colors[j*4+2]; c[i*4+3] = data.colors[j*4+3]
    r[i*4] = data.rotations[j*4]; r[i*4+1] = data.rotations[j*4+1]; r[i*4+2] = data.rotations[j*4+2]; r[i*4+3] = data.rotations[j*4+3]
  }
  return { p, s, c, r }
}

export default function GaussianSplatViewer({ url, file, className = '', onLoad }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [count, setCount] = useState(0)
  const [isFs, setIsFs] = useState(false)

  const toggleFs = () => {
    const el = wrapRef.current
    if (!el) return
    if (document.fullscreenElement) document.exitFullscreen()
    else el.requestFullscreen()
    setIsFs(!isFs)
  }

  useEffect(() => {
    const cvs = canvasRef.current
    if (!cvs || (!url && !file)) return
    let dead = false, animId = 0, worker: Worker | null = null

    async function run() {
      const canvas = cvs!
      try {
        const buf = file ? await file.arrayBuffer()
          : await fetch(url!).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.arrayBuffer() })
        if (dead) return

        const data = parseSplat(buf)
        setCount(data.count); setLoading(false); onLoad?.(data.count)

        const gl = canvas.getContext('webgl2', { antialias: false, alpha: false })!
        if (!gl) throw new Error('WebGL2 not supported on this device')

        const prog = linkProgram(gl, VERT, FRAG)
        gl.useProgram(prog)

        const loc = {
          quad: gl.getAttribLocation(prog, 'a_quad'),
          center: gl.getAttribLocation(prog, 'a_center'),
          scale: gl.getAttribLocation(prog, 'a_scale'),
          color: gl.getAttribLocation(prog, 'a_color'),
          rot: gl.getAttribLocation(prog, 'a_rot'),
          view: gl.getUniformLocation(prog, 'u_view')!,
          proj: gl.getUniformLocation(prog, 'u_proj')!,
          focal: gl.getUniformLocation(prog, 'u_focal')!,
          vp: gl.getUniformLocation(prog, 'u_viewport')!,
        }

        const vao = gl.createVertexArray()!
        gl.bindVertexArray(vao)

        const qb = gl.createBuffer()!
        gl.bindBuffer(gl.ARRAY_BUFFER, qb)
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-2, -2, 2, -2, 2, 2, -2, 2]), gl.STATIC_DRAW)
        gl.enableVertexAttribArray(loc.quad)
        gl.vertexAttribPointer(loc.quad, 2, gl.FLOAT, false, 0, 0)

        const ib = gl.createBuffer()!
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib)
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array([0, 1, 2, 0, 2, 3]), gl.STATIC_DRAW)

        function instBuf(attr: number, size: number, type: number, norm: boolean, bytes: number) {
          const b = gl.createBuffer()!
          gl.bindBuffer(gl.ARRAY_BUFFER, b)
          gl.bufferData(gl.ARRAY_BUFFER, bytes, gl.DYNAMIC_DRAW)
          gl.enableVertexAttribArray(attr)
          gl.vertexAttribPointer(attr, size, type, norm, 0, 0)
          gl.vertexAttribDivisor(attr, 1)
          return b
        }

        const bufs = {
          center: instBuf(loc.center, 3, gl.FLOAT, false, data.count * 12),
          scale: instBuf(loc.scale, 3, gl.FLOAT, false, data.count * 12),
          color: instBuf(loc.color, 4, gl.UNSIGNED_BYTE, true, data.count * 4),
          rot: instBuf(loc.rot, 4, gl.FLOAT, false, data.count * 16),
        }
        gl.bindVertexArray(null)

        gl.enable(gl.BLEND)
        gl.blendFuncSeparate(gl.ONE_MINUS_DST_ALPHA, gl.ONE, gl.ONE_MINUS_DST_ALPHA, gl.ONE)
        gl.depthMask(false); gl.disable(gl.DEPTH_TEST)

        let cx = 0, cy = 0, cz = 0
        for (let i = 0; i < data.count; i++) {
          cx += data.positions[i * 3]; cy += data.positions[i * 3 + 1]; cz += data.positions[i * 3 + 2]
        }
        cx /= data.count; cy /= data.count; cz /= data.count

        let maxR = 0
        const sampleStep = Math.max(1, Math.floor(data.count / 10000))
        for (let i = 0; i < data.count; i += sampleStep) {
          const dx = data.positions[i * 3] - cx, dy = data.positions[i * 3 + 1] - cy, dz = data.positions[i * 3 + 2] - cz
          maxR = Math.max(maxR, Math.sqrt(dx * dx + dy * dy + dz * dz))
        }

        const cam = { theta: 0.5, phi: 0.3, radius: Math.max(maxR * 1.5, 2), target: [cx, cy, cz] as V3, dirty: true }

        worker = createSortWorker()
        let sortPending = false, curView: Float32Array = new Float32Array(16)

        worker.onmessage = ({ data: indices }) => {
          sortPending = false
          const sorted = reorder(data, indices as Uint32Array)
          gl.bindBuffer(gl.ARRAY_BUFFER, bufs.center); gl.bufferSubData(gl.ARRAY_BUFFER, 0, sorted.p)
          gl.bindBuffer(gl.ARRAY_BUFFER, bufs.scale); gl.bufferSubData(gl.ARRAY_BUFFER, 0, sorted.s)
          gl.bindBuffer(gl.ARRAY_BUFFER, bufs.color); gl.bufferSubData(gl.ARRAY_BUFFER, 0, sorted.c)
          gl.bindBuffer(gl.ARRAY_BUFFER, bufs.rot); gl.bufferSubData(gl.ARRAY_BUFFER, 0, sorted.r)
        }

        function requestSort(view: Float32Array) {
          if (sortPending) return
          sortPending = true; curView = view
          worker!.postMessage({
            positions: new Float32Array(data.positions),
            viewRow: [view[2], view[6], view[10], view[14]],
            count: data.count,
          })
        }

        let dragging = false, lx = 0, ly = 0, pinchD = 0
        canvas.addEventListener('mousedown', e => { dragging = true; lx = e.clientX; ly = e.clientY })
        canvas.addEventListener('mousemove', e => {
          if (!dragging) return
          cam.theta -= (e.clientX - lx) * 0.005
          cam.phi = Math.max(-1.5, Math.min(1.5, cam.phi + (e.clientY - ly) * 0.005))
          lx = e.clientX; ly = e.clientY; cam.dirty = true
        })
        canvas.addEventListener('mouseup', () => { dragging = false })
        canvas.addEventListener('mouseleave', () => { dragging = false })
        canvas.addEventListener('wheel', e => {
          e.preventDefault()
          cam.radius = Math.max(0.3, Math.min(100, cam.radius * (1 + e.deltaY * 0.001)))
          cam.dirty = true
        }, { passive: false })

        canvas.addEventListener('touchstart', e => {
          e.preventDefault()
          const t = e.touches
          if (t.length === 1) { lx = t[0].clientX; ly = t[0].clientY }
          if (t.length === 2) pinchD = Math.hypot(t[1].clientX - t[0].clientX, t[1].clientY - t[0].clientY)
        }, { passive: false })
        canvas.addEventListener('touchmove', e => {
          e.preventDefault()
          const t = e.touches
          if (t.length === 1) {
            cam.theta -= (t[0].clientX - lx) * 0.005
            cam.phi = Math.max(-1.5, Math.min(1.5, cam.phi + (t[0].clientY - ly) * 0.005))
            lx = t[0].clientX; ly = t[0].clientY; cam.dirty = true
          }
          if (t.length === 2) {
            const d = Math.hypot(t[1].clientX - t[0].clientX, t[1].clientY - t[0].clientY)
            if (pinchD > 0) { cam.radius = Math.max(0.3, Math.min(100, cam.radius * (pinchD / d))); cam.dirty = true }
            pinchD = d
          }
        }, { passive: false })
        canvas.addEventListener('touchend', e => { if (e.touches.length < 2) pinchD = 0 })

        const eye = (): V3 => [
          cam.target[0] + cam.radius * Math.sin(cam.theta) * Math.cos(cam.phi),
          cam.target[1] + cam.radius * Math.sin(cam.phi),
          cam.target[2] + cam.radius * Math.cos(cam.theta) * Math.cos(cam.phi),
        ]

        requestSort(lookAt(eye(), cam.target, [0, 1, 0]))

        function frame() {
          if (dead) return
          const rect = canvas.getBoundingClientRect()
          const dpr = Math.min(window.devicePixelRatio || 1, 2)
          const w = Math.round(rect.width * dpr), h = Math.round(rect.height * dpr)
          if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h }

          const view = lookAt(eye(), cam.target, [0, 1, 0])
          const fov = Math.PI / 4
          const proj = perspective(fov, w / h, 0.1, 200)
          const fy = h / (2 * Math.tan(fov / 2))

          if (cam.dirty) { cam.dirty = false; requestSort(view) }

          gl.viewport(0, 0, w, h)
          gl.clearColor(0.04, 0.04, 0.043, 1)
          gl.clear(gl.COLOR_BUFFER_BIT)
          gl.useProgram(prog)
          gl.uniformMatrix4fv(loc.view, false, curView)
          gl.uniformMatrix4fv(loc.proj, false, proj)
          gl.uniform2f(loc.focal, fy, fy)
          gl.uniform2f(loc.vp, w, h)
          gl.bindVertexArray(vao)
          gl.drawElementsInstanced(gl.TRIANGLES, 6, gl.UNSIGNED_SHORT, 0, data.count)
          animId = requestAnimationFrame(frame)
        }
        animId = requestAnimationFrame(frame)
      } catch (e: any) {
        if (!dead) { setError(e.message || 'Failed to load'); setLoading(false) }
      }
    }
    run()
    return () => { dead = true; cancelAnimationFrame(animId); worker?.terminate() }
  }, [url, file])

  return (
    <div ref={wrapRef} className={`relative rounded-xl overflow-hidden bg-[#0A0A0B] border border-[#1F1F23] ${className}`}>
      <canvas ref={canvasRef} className="w-full h-full block" style={{ touchAction: 'none' }} />
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0A0A0B]">
          <div className="text-center">
            <Loader2 size={24} className="text-[#1A8FD6] animate-spin mx-auto mb-2" />
            <p className="text-xs text-[#A1A1A8]">Loading 3D scene...</p>
          </div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0A0A0B]">
          <div className="text-center px-4">
            <p className="text-sm text-red-400 font-medium">Failed to load</p>
            <p className="text-xs text-[#A1A1A8] mt-1">{error}</p>
          </div>
        </div>
      )}
      {!loading && !error && (
        <>
          <div className="absolute top-3 right-3 flex items-center gap-2">
            <div className="px-2.5 py-1.5 rounded-lg bg-[#0A0A0B]/80 border border-[#1F1F23]">
              <p className="text-[10px] font-mono text-[#17C5B0]">{count.toLocaleString()} splats</p>
            </div>
            <button onClick={toggleFs}
              className="p-2 rounded-lg bg-[#0A0A0B]/80 border border-[#1F1F23] text-[#A1A1A8] hover:text-white transition-colors">
              {isFs ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          </div>
          <div className="absolute bottom-3 left-3 px-2.5 py-1.5 rounded-lg bg-[#0A0A0B]/80 border border-[#1F1F23]">
            <p className="text-[9px] text-[#A1A1A8]">Drag to orbit &middot; Pinch to zoom</p>
          </div>
        </>
      )}
    </div>
  )
}
