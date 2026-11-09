import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';

const base = process.env.CANCEROS_BROWSER_BASE_URL ?? 'http://127.0.0.1:3000';
const output = process.env.CANCEROS_BROWSER_EVIDENCE_DIR ? `${process.env.CANCEROS_BROWSER_EVIDENCE_DIR}/viewer` : 'docs/engineering/testing/rec03-viewer';

test('REC-03 immersive viewer: toolbar, states, correspondence, recovery, layouts', async ({ page }) => {
  test.setTimeout(420000);
  page.setViewportSize({ width: 1440, height: 1000 });
  mkdirSync(output, { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message.slice(0, 200)));
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|Failed to load resource/i.test(message.text())) errors.push(message.text().slice(0, 200));
  });

  // 1. Demo twin: compact toolbar present, baseline state and volume visible.
  await page.goto(`${base}/demo?view=twin`);
  await expect(page.getByText(/Shared baseline/i).first()).toBeVisible({ timeout: 60000 });
  const toolbar = page.getByRole('toolbar', { name: 'Camera controls' });
  await expect(toolbar).toBeVisible();
  for (const name of ['Orbit', 'Zoom in', 'Zoom out', 'Fit view', 'Reset view', 'Maximize viewer', 'Fullscreen viewer']) {
    await expect(toolbar.getByRole('button', { name, exact: true })).toBeVisible();
  }
  await expect(page.getByText('216', { exact: true }).first()).toBeVisible({ timeout: 30000 });
  const canvas = page.locator('#demo-measurements, section[aria-label="Selected digital twin"]').first().locator('canvas').first();
  await expect(canvas).toBeVisible({ timeout: 60000 });
  const box = await canvas.boundingBox();
  expect(box, 'viewer canvas box').not.toBeNull();
  expect(box!.width, 'viewer dominates the content width').toBeGreaterThan(600);
  expect(box!.height, 'viewer is substantially tall').toBeGreaterThan(500);
  await page.screenshot({ path: `${output}/01-twin-baseline.png`, fullPage: true });

  // 2. Orbit, pan, zoom, fit via toolbar buttons.
  const before = await canvas.screenshot();
  const zoomGroup = toolbar.getByRole('group', { name: 'Zoom' });
  const frameGroup = toolbar.getByRole('group', { name: 'Framing' });
  await toolbar.getByText('More camera controls').click();
  await toolbar.getByRole('button', { name: 'Rotate right', exact: true }).first().click();
  await toolbar.getByRole('button', { name: 'Pan right', exact: true }).first().click();
  await page.waitForTimeout(800);
  const orbited = await canvas.screenshot();
  expect(orbited.equals(before)).toBe(false);
  await zoomGroup.getByRole('button', { name: 'Zoom in', exact: true }).click();
  await frameGroup.getByRole('button', { name: 'Fit view', exact: true }).click();
  await page.waitForTimeout(800);

  // 3. Maximize the renderer and return.
  await toolbar.getByRole('button', { name: 'Maximize viewer', exact: true }).click();
  await expect(toolbar.getByRole('button', { name: 'Restore viewer size', exact: true })).toBeVisible();
  await expect(page.getByLabel('Scenario timeline')).toBeVisible();
  await page.screenshot({ path: `${output}/02-viewer-maximized.png` });
  await toolbar.getByRole('button', { name: 'Restore viewer size', exact: true }).click();
  await expect(toolbar.getByRole('button', { name: 'Maximize viewer', exact: true })).toBeVisible();
  await toolbar.getByRole('button', { name: 'Fullscreen viewer', exact: true }).click();
  await expect.poll(() => page.evaluate(() => !!document.fullscreenElement)).toBe(true);
  await expect(page.getByLabel('Scenario timeline')).toBeVisible();
  await toolbar.getByRole('button', { name: 'Exit fullscreen', exact: true }).click();
  await expect.poll(() => page.evaluate(() => !!document.fullscreenElement)).toBe(false);

  // 4. Select Day 37 follow-up: model and measurement change together.
  await page.getByRole('button', { name: /Day 37/ }).first().click();
  await expect(page.getByText('64', { exact: true }).first()).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('Day 37', { exact: true }).first()).toBeVisible({ timeout: 30000 });
  const chartPoint = page.getByRole('button', { name: /Day 37: 64/ });
  await expect(chartPoint.first()).toHaveAttribute('aria-pressed', 'true');
  await page.screenshot({ path: `${output}/03-followup-day37.png`, fullPage: true });

  // 5. Refresh and navigation recovery keep the selection.
  await page.reload();
  await expect(page.getByText('64', { exact: true }).first()).toBeVisible({ timeout: 60000 });
  await expect(page.locator('canvas').first()).toBeVisible({ timeout: 60000 });

  // 6. Narrow screen keeps controls usable.
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(toolbar.getByRole('button', { name: 'Fit view', exact: true })).toBeVisible();
  const narrowCamera = await canvas.getAttribute('data-camera-state');
  await toolbar.getByRole('button', { name: 'Zoom in', exact: true }).click();
  await expect(canvas).not.toHaveAttribute('data-camera-state', narrowCamera!);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: `${output}/04-narrow.png`, fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1000 });

  // 7. WebGL failure recovery: force context loss, expect the recovery panel.
  await page.goto(`${base}/demo?view=twin`);
  await expect(page.locator('canvas').first()).toBeVisible({ timeout: 60000 });
  const lost = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return 'no-canvas';
    const ext = (canvas.getContext('webgl2') ?? canvas.getContext('webgl'))?.getExtension('WEBGL_lose_context');
    if (!ext) return 'no-extension';
    ext.loseContext();
    return 'lost';
  });
  expect(lost).toBe('lost');
  await expect(page.getByText('The 3D view could not load')).toBeVisible({ timeout: 30000 });
  await page.screenshot({ path: `${output}/05-webgl-recovery.png` });
  await page.getByRole('button', { name: 'Retry 3D viewer' }).click();
  await expect(page.locator('canvas').first()).toBeVisible({ timeout: 60000 });

  expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
  writeFileSync(`${output}/rec03-viewer-evidence.json`, JSON.stringify({
    recorded_at: new Date().toISOString(),
    scope: 'Fresh demo bundle on restarted foundation; synthetic phantom only, no authentic anatomy',
    journey: ['toolbar', 'orbit-pan-zoom-fit', 'maximize', 'day37-correspondence', 'refresh', 'narrow', 'webgl-recovery'],
    browser_errors: errors,
  }, null, 2));
});
