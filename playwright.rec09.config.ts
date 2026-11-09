import { defineConfig } from '@playwright/test';

process.env.CANCEROS_BROWSER_BASE_URL = 'http://127.0.0.1:3001';
process.env.CANCEROS_BROWSER_EVIDENCE_DIR = 'docs/engineering/testing/rec09-acceptance';
export default defineConfig({
  testDir: './tests/browser',
  testMatch: ['rec09-acceptance.spec.ts'],
  workers: 1,
  outputDir: '.local/rec09-playwright',
  reporter: [['list'], ['json', { outputFile: '.local/rec09-playwright-results.json' }]],
  use: { browserName: 'chromium', headless: true, actionTimeout: 20000, navigationTimeout: 30000 },
  webServer: {
    command: 'node node_modules/next/dist/bin/next start apps/web --hostname 127.0.0.1 --port 3001',
    url: 'http://127.0.0.1:3001',
    reuseExistingServer: false,
    timeout: 120000,
    env: { API_BASE_URL: 'http://127.0.0.1:8001', CANCEROS_SYNTHETIC_DEMO: '1', EXTERNAL_INFERENCE_ENABLED: 'false' },
  },
});
