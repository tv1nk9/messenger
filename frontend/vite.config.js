import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Дев-сервер проксирует REST/WS на FastAPI (порт 8000),
// поэтому во время разработки достаточно открыть http://localhost:5173
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  base: '/static/react/',
  build: {
    outDir: '../static/react',
    emptyOutDir: true,
  },
});
