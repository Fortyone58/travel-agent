import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 开发时：前端请求 /api → 代理到 FastAPI 后端（8000）
      '/api': 'http://127.0.0.1:8000'
    }
  }
})
