import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const target = loadEnv(mode, '.', 'NAGARSEVA_').NAGARSEVA_API_TARGET || 'http://127.0.0.1:8000'
  return {
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': { target, rewrite: path => path.replace(/^\/api/, '') } } },
  preview: { port: 4173, proxy: { '/api': { target, rewrite: path => path.replace(/^\/api/, '') } } },
  build: { rollupOptions: { output: { manualChunks: { charts: ['recharts'], maps: ['leaflet', 'react-leaflet'] } } } },
}
})
