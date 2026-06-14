import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, forward /api/* to the Python backend (`hearing serve`) so the browser
// talks to one origin (no CORS dance). In prod you'd serve the built assets
// behind the same host as the API.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
});
