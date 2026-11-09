import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser', testMatch: ['rec-audit-upload.spec.ts'], workers: 1,
  outputDir: '.local/audit-upload-playwright',
  reporter: [['list'], ['json', { outputFile: '.local/audit-upload-playwright-results.json' }]],
  webServer: {
    command: 'node node_modules/next/dist/bin/next start apps/web --hostname 127.0.0.1 --port 3001',
    url: 'http://127.0.0.1:3001', reuseExistingServer: false, timeout: 120000,
    env: { API_BASE_URL: 'http://127.0.0.1:8001', CANCEROS_SYNTHETIC_DEMO: '1', EXTERNAL_INFERENCE_ENABLED: 'false' },
  },
  use: { browserName: 'chromium', headless: true, actionTimeout: 20000, navigationTimeout: 30000 },
});
