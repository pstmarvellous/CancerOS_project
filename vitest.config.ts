import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./apps/web/test-setup.ts'],
    include: ['apps/web/**/*.test.tsx'],
    maxWorkers: 2,
  },
});
