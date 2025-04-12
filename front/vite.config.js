import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/ui/',
  server: {
    historyApiFallback: true, // ← 이 줄 추가
  }
});
