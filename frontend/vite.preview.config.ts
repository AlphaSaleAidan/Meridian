// Build config for the Bookings preview page only. Separate from
// vite.config.ts so the real app's entry, chunking and output are untouched.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    outDir: 'dist-preview',
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, 'preview.html'),
    },
  },
})
