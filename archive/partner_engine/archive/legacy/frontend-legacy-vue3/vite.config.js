import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_DEV_API_TARGET || 'http://localhost:8080'

  return {
    plugins: [vue()],
    build: {
      sourcemap: false,
      reportCompressedSize: false,
      chunkSizeWarningLimit: 1600,
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ['vue'],
            element: ['element-plus'],
            charts: ['echarts'],
            three: ['three']
          }
        }
      }
    },
    server: {
      host: '0.0.0.0',
      port: Number(env.VITE_PORT || 5173),
      strictPort: true,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true
        },
        '/ws': {
          target: backendTarget,
          changeOrigin: true,
          ws: true
        }
      }
    }
  }
})
