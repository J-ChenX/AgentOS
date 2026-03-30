import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  // In test mode, force the mock adapter so tests never make real HTTP calls.
  define:
    mode === 'test'
      ? {
          'import.meta.env.VITE_ADAPTER': '"mock"',
          'import.meta.env.VITE_API_URL': '""',
        }
      : {},
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
}));
