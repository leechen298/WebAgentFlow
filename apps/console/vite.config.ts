import { fileURLToPath, URL } from 'node:url';
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const port = Number(env.CONSOLE_PORT ?? 5174);
  const apiPort = Number(env.API_PORT ?? 8001);
  const useDevProxy = env.VITE_USE_DEV_PROXY === 'true';

  const config: ReturnType<typeof defineConfig> = {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port,
    },
  };

  // Optional dev proxy - only enabled when VITE_USE_DEV_PROXY=true
  if (useDevProxy && config.server) {
    config.server.proxy = {
      '/api': {
        target: `http://localhost:${apiPort}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    };
  }

  return config;
});
