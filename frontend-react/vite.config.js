import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), basicSsl()],
  server: {
    host: true, // or use '0.0.0.0' to listen on all addresses
    port: 5173, // default port
    https: true, // Enable HTTPS
  }
})
