import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/token': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/validate-chart': 'http://localhost:8000',
      '/metrics': 'http://localhost:8000',
      '/history': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})
