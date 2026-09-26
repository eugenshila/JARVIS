import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    hmr: {
      clientPort: 443,
    },
    // Allow all hosts for preview environment
    allowedHosts: true as any,
    cors: true,
    headers: {
      'X-Frame-Options': 'ALLOWALL',
    },
    proxy: {
      '/v1': 'http://localhost:8000',
      '/run': 'http://localhost:8000',
      '/agents': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/memory': 'http://localhost:8000',
      '/skills': 'http://localhost:8000',
      '/telemetry': 'http://localhost:8000',
      '/engines': 'http://localhost:8000',
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 4173
  }
})
