import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/busbar-viewer/',
  define: {
    // Some AWS SDK modules reference global/process — provide safe shims
    global: 'globalThis',
  },
});