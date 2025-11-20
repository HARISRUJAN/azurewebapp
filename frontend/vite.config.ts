import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allow network access
    port: 5173,
    // Ensure SPA routing works - serve index.html for all routes
    // This is the default behavior in Vite, but explicitly configured for clarity
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  // Build configuration for production
  build: {
    rollupOptions: {
      input: {
        main: './index.html',
      },
    },
  },
})

