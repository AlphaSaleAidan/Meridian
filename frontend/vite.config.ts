import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  // Preview tunnels (cloudflared) present a random hostname; without this the
  // preview server 403s them and the review link is dead on arrival.
  preview: { allowedHosts: true },
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // FUNCTION form, not the object map. The object form makes Rollup
        // hoist a shared commonjs-interop helper into every manual chunk,
        // which turns the entry chunk into a STATIC importer of vendor-three
        // (1.1MB) / vendor-pdf / vendor-charts — all render-blocking on the
        // landing page even though every consumer is behind React.lazy.
        // With the function form only the matched modules are assigned, the
        // helper stays where it's used, and the heavy vendors load on demand.
        manualChunks(id: string) {
          // Vite/Rollup VIRTUAL helper modules (the dynamic-import preload
          // helper, commonjs interop) and tiny shared utils like clsx: left
          // unassigned, Rollup colocates them into whichever vendor chunk it
          // emits first — which turns the entry into a static importer of
          // vendor-pdf / vendor-charts all over again. Pin them to 'vendor'
          // (always preloaded anyway). The virtual-id check must run BEFORE
          // the node_modules gate — virtual ids don't contain node_modules.
          if (id.startsWith('\0vite/') || id.includes('commonjsHelpers')) return 'vendor'
          if (!id.includes('node_modules')) return undefined
          if (id.includes('/node_modules/clsx/')) return 'vendor'
          if (
            id.includes('/node_modules/three/') ||
            id.includes('/node_modules/three-stdlib/') ||
            id.includes('@react-three/fiber') ||
            id.includes('@react-three/drei')
          ) return 'vendor-three'
          if (id.includes('postprocessing')) return 'vendor-postprocessing'
          if (id.includes('/node_modules/jspdf') || id.includes('html2canvas')) return 'vendor-pdf'
          if (id.includes('/node_modules/recharts')) return 'vendor-charts'
          if (id.includes('/node_modules/framer-motion/')) return 'vendor-motion'
          if (id.includes('@supabase/')) return 'vendor-supabase'
          if (id.includes('/node_modules/lucide-react/')) return 'vendor-lucide'
          if (
            id.includes('/node_modules/react/') ||
            id.includes('/node_modules/react-dom/') ||
            id.includes('/node_modules/react-router/') ||
            id.includes('/node_modules/react-router-dom/') ||
            id.includes('/node_modules/scheduler/')
          ) return 'vendor'
          return undefined
        },
      },
    },
  },
  server: {
    port: 3000,
    allowedHosts: true,
    hmr: process.env.VITE_HMR_HOST ? { host: process.env.VITE_HMR_HOST } : undefined,
    proxy: {
      '/api': {
        // Overridable so a preview/dev server can point at a non-default
        // backend port (the box's :8000 is the live pm2 API).
        target: process.env.MERIDIAN_API_PROXY || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
