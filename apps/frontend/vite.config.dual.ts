import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// 本地双后端配置：/api 走 _demo_p0 后端（8000），/local-pg 走 R30-E 后端（8001）。
// 不改默认 vite.config.ts，避免影响既有演示与队友的开发流程。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/local-pg': 'http://127.0.0.1:8001',
    },
  },
});
