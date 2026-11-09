import { defineConfig } from '@playwright/test';

process.env.CANCEROS_BROWSER_BASE_URL = 'http://127.0.0.1:3001';
process.env.CANCEROS_BROWSER_EVIDENCE_DIR = 'docs/engineering/testing/rec00-reverify';

export default defineConfig({
  testDir: './tests/browser',
  testMatch: ['rec01-navigation.spec.ts', 'rec02-demo.spec.ts', 'rec05-cases.spec.ts', 'ux-recovery.spec.ts'],
  grep: /REC-|demo boundaries/,
  workers: 1,
  outputDir: '.local/rec00-playwright',
  reporter: [['list'], ['json', { outputFile: '.local/rec00-browser-results.json' }]],
  use: { browserName: 'chromium', headless: true },
  webServer: {
    command: 'node node_modules/next/dist/bin/next start apps/web --hostname 127.0.0.1 --port 3001',
    url: 'http://127.0.0.1:3001',
    reuseExistingServer: false,
    timeout: 60000,
    env: { API_BASE_URL: 'http://127.0.0.1:8001', CANCEROS_SYNTHETIC_DEMO: '1', EXTERNAL_INFERENCE_ENABLED: 'false' },
  },
});
