import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

// Minimal Vitest setup for the canada-portal hook tests. Kept separate
// from vite.config.ts so the production build is untouched and adding
// future test files doesn't disturb the dev/build pipeline.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/__tests__/**/*.test.{ts,tsx}'],
    css: false,
  },
})
