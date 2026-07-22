import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
 server: {
  host: "0.0.0.0",
  port: 5173,
  allowedHosts: true, 

  proxy: {
    '/health': 'http://localhost:8000',
    '/audit':  'http://localhost:8000',
    '/screenshots':  'http://localhost:8000',
    '/export':       'http://localhost:8000',
  },
},
})
