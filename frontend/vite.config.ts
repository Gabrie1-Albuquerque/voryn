import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    // Nginx proxies the browser here; HMR websocket must reconnect through
    // the same host:port the browser used, not the container-internal one.
    hmr: {
      clientPort: 80,
    },
    watch: {
      usePolling: true,
    },
  },
})
