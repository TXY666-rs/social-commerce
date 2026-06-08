import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5174,
    host: '127.0.0.1',
    proxy: {
      // 代理后端API请求，通过网关访问微服务
      '/api': {
        target: 'http://localhost:9000',
        changeOrigin: true
      }
    }
  }
})
