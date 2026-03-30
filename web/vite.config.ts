import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    css: true,
    passWithNoTests: true,
  },
  server: {
    port: 6493,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
