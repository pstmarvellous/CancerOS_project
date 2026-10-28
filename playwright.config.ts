import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  use: {browserName:'chromium',headless:true},
  webServer: {command:'npm run start',url:'http://127.0.0.1:3000',reuseExistingServer:!process.env.CI,timeout:60000},
});
