import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    // No hmr.clientPort override: Vite's HMR client defaults to
    // window.location's own host:port, which is correct whichever way this
    // gets accessed (directly on 5173, or proxied through nginx on 8080 --
    // see docker/nginx/conf.d/default.conf's `location /`, which already
    // forwards the Upgrade/Connection headers HMR's websocket needs).
    // Hardcoding a specific port here would only be right for one of those
    // two paths.
    watch: {
      usePolling: true,
    },
    proxy: {
      // Lets the frontend work standalone on :5173 (e.g. this Preview tool,
      // or `npm run dev` outside Docker) without depending on nginx --
      // `backend` resolves via Docker's internal DNS since this proxying
      // happens inside the Vite dev server process, not in the browser.
      '/api': { target: 'http://backend:8000', changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, '') },
      '/public': { target: 'http://backend:8000', changeOrigin: true },
    },
  },
})
