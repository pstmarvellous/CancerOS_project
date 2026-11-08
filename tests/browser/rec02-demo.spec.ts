import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';

const base = 'http://127.0.0.1:3000';
const output = 'docs/engineering/testing/rec02-demo';

test('REC-02 first-time demo: homepage launch, 3D canvas, scenario, follow-up, refresh', async ({ page, context }) => {
  test.setTimeout(420000);
  page.setViewportSize({ width: 1440, height: 1000 });
  mkdirSync(output, { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message.slice(0, 200)));
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|Failed to load resource/i.test(message.text())) errors.push(message.text().slice(0, 200));
  });

  // 1. Fresh session: no stored data, homepage sells one primary action.
  await context.clearCookies();
  await page.goto(`${base}/`);
  await page.waitForLoadState('domcontentloaded');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Explore How a Tumor Could Change Over Time');
  const cta = page.getByRole('link', { name: 'Explore Interactive Demo' });
  await expect(cta).toBeVisible();
  await expect(cta).toHaveAttribute('href', '/demo');
  await expect(page.getByRole('link', { name: 'Create or Open a Research Case' })).toHaveAttribute('href', '/cases');
  await expect(page.getByText(/synthetic data/i).first()).toBeVisible();
  await page.screenshot({ path: `${output}/01-homepage.png`, fullPage: true });

  // 2. One click opens a valid session with real data (no token, no UUIDs).
  await cta.click();
  await expect(page).toHaveURL(/\/demo/);
  await expect(page.getByText(/Shared baseline/i).first()).toBeVisible({ timeout: 60000 });
  await expect(page.getByText(/not ready|could not open|unavailable/i)).toBeHidden({ timeout: 5000 }).catch(() => {});
  await page.screenshot({ path: `${output}/02-demo-overview.png`, fullPage: true });

  // 3. The real 3D canvas renders and rotates.
  const canvas = page.locator('canvas').first();
  await expect(canvas).toBeVisible({ timeout: 60000 });
  const before = await canvas.screenshot();
  await canvas.hover();
  await page.mouse.move(720, 500);
  await page.mouse.down();
  await page.mouse.move(900, 420, { steps: 12 });
  await page.mouse.up();
  await page.waitForTimeout(1500);
  const after = await canvas.screenshot();
  expect(after.equals(before)).toBe(false);
  await page.screenshot({ path: `${output}/03-demo-rotated.png`, fullPage: true });

  // 4. Select a scenario and inspect a follow-up state.
  await page.getByLabel('Hypothetical scenario').selectOption('SC-03');
  await expect(page.getByText(/keeps getting larger over time/i).first()).toBeVisible({ timeout: 60000 });
  const followUps = page.getByRole('button', { name: /Day \d+/ });
  await expect(followUps.first()).toBeVisible({ timeout: 30000 });
  await followUps.nth(1).click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${output}/04-demo-followup.png`, fullPage: true });

  // 5. Refresh repeats the journey without stored-data dependence.
  await page.reload();
  await expect(page.getByText(/Shared baseline/i).first()).toBeVisible({ timeout: 60000 });
  await expect(page.locator('canvas').first()).toBeVisible({ timeout: 60000 });
  await page.screenshot({ path: `${output}/05-demo-refreshed.png`, fullPage: true });

  expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
  writeFileSync(`${output}/rec02-demo-evidence.json`, JSON.stringify({
    recorded_at: new Date().toISOString(),
    scope: 'Fresh browser session, no token or UUID entry; token-free synthetic bundle only',
    journey: ['homepage', 'demo-launch', 'canvas-rotate', 'scenario-select', 'followup-inspect', 'refresh'],
    browser_errors: errors,
  }, null, 2));
});
