import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// /api는 백엔드 기본 주소로 넘긴다. docs/design/AppSkeleton.md 3절 참조.
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
