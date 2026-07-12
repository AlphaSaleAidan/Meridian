// Preview-only reverse proxy: mirrors prod nginx routing for tunnel previews.
// Static assets → local `vite preview` (:4611); /api/* → prod backend.
// Usage: node scripts/preview-proxy.mjs [port]
import http from 'node:http'
import https from 'node:https'

const PORT = Number(process.argv[2] || 4610)
const STATIC_HOST = 'localhost'
const STATIC_PORT = 4611
const API_HOST = 'api.meridian.tips'

const server = http.createServer((req, res) => {
  const isApi = req.url.startsWith('/api/') || req.url === '/api'
  const headers = { ...req.headers }
  delete headers['accept-encoding'] // keep bodies inspectable / avoid double-encoding
  if (isApi) {
    headers.host = API_HOST
    const upstream = https.request(
      { host: API_HOST, port: 443, path: req.url, method: req.method, headers },
      up => { res.writeHead(up.statusCode || 502, up.headers); up.pipe(res) },
    )
    upstream.on('error', () => { res.writeHead(502); res.end('upstream error') })
    req.pipe(upstream)
  } else {
    headers.host = `${STATIC_HOST}:${STATIC_PORT}`
    const upstream = http.request(
      { host: STATIC_HOST, port: STATIC_PORT, path: req.url, method: req.method, headers },
      up => { res.writeHead(up.statusCode || 502, up.headers); up.pipe(res) },
    )
    upstream.on('error', () => { res.writeHead(502); res.end('static server down') })
    req.pipe(upstream)
  }
})

server.listen(PORT, () => console.log(`preview proxy on :${PORT} (static :${STATIC_PORT}, /api -> ${API_HOST})`))
