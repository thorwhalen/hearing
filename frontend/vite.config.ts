import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Mount path: enlace's deployer injects VITE_PUBLIC_BASE=/hearing/ at build time
// (the thoremin pattern). Locally we default to './' (relative) so the build also
// works at the root. `server.fs.allow: ['..']` lets the dev server read the repo's
// misc/docs/MANUAL.md (imported with ?raw); the production build bundles it regardless.
export default defineConfig({
  base: process.env.VITE_PUBLIC_BASE || './',
  plugins: [react()],
  server: {
    port: 5173,
    fs: { allow: ['..'] },
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
});
