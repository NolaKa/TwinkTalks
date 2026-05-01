import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, FastAPI runs on :7860 and Vite on :5173.
// Proxying /api keeps fetch + EventSource same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:7860',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
