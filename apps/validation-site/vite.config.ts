import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// Dev proxy forwards /validation-api/* to the FastAPI backend at localhost:8001.
// This avoids CORS in development and keeps the frontend calling a same-origin path.
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5175,
    strictPort: true,
    proxy: {
      '/validation-api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
});
