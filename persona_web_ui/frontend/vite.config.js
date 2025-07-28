import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '')
  
  // Get ports from environment variables with fallbacks
  const frontendPort = parseInt(env.FRONTEND_PORT || '5173')
  const backendPort = parseInt(env.WEB_UI_PORT || '8000')
  
  return {
    plugins: [react()],
    server: {
      port: frontendPort,
      strictPort: false, // Allow port increment if occupied
      proxy: {
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
          secure: false,
        }
      }
    }
  }
})