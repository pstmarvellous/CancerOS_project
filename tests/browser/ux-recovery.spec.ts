import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';

const base = process.env.CANCEROS_BROWSER_BASE_URL ?? 'http://127.0.0.1:3000';
const output = 'docs/engineering/testing/ux-recovery';
test.use({ actionTimeout: 15000 });

test('first-time digital twin journey: actual WebGL, all scenarios, history and observations', async ({ page, context }) => {
  test.setTimeout(360000);
  await context.clearCookies();
  await page.setViewportSize({ width: 1440, height: 1100 });
  mkdirSync(output, { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const backendRequests: string[] = [];
  page.on('request', request => { if (request.url().includes(':8000')) backendRequests.push(request.url()); });
  await page.goto(base);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Evolution in 3D');
  await expect(page.getByRole('button', { name: 'Check API connection' })).toHaveCount(0);
  await page.screenshot({ path: `${output}/01-home.png`, fullPage: true });
  await page.getByRole('link', { name: 'Launch Digital Twin Demo', exact: true }).click();
  const canvas = page.locator('canvas[data-render-ready=true]');
  await expect(canvas).toBeVisible({ timeout: 60000 });
  await expect(page.getByTestId('demo-volume')).toHaveText('216 mm³');
  await expect(page.getByRole('textbox')).toHaveCount(0);
  const cookies = await context.cookies();
  const session = cookies.find(c => c.name === 'canceros-synthetic-demo');
  expect(session?.httpOnly).toBe(true);
  expect(session?.sameSite).toBe('Strict');
  const initial = await canvas.getAttribute('data-camera-state');
  for (const button of ['Rotate left', 'Pan right', 'Zoom in']) {
    const before = await canvas.getAttribute('data-camera-state');
    await page.getByRole('button', { name: button, exact: true }).click();
    await expect(canvas).not.toHaveAttribute('data-camera-state', before!);
  }
  await page.getByRole('button', { name: 'Reset view', exact: true }).click();
  await expect(canvas).toHaveAttribute('data-camera-state', initial!);
  await page.getByRole('button', { name: 'Interact with 3D', exact: true }).click();
  const box = await canvas.boundingBox();
  const beforeDrag = await canvas.getAttribute('data-camera-state');
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.down(); await page.mouse.move(box!.x + box!.width / 2 + 65, box!.y + box!.height / 2 + 30, { steps: 6 }); await page.mouse.up();
  await expect(canvas).not.toHaveAttribute('data-camera-state', beforeDrag!);
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Reset view', exact: true }).click();
  await page.screenshot({ path: `${output}/02-twin-baseline.png`, fullPage: true });
  const timelineButtons = page.locator('[aria-label="Scenario timeline"]');
  await timelineButtons.getByRole('button', { name: /Day 37/ }).click();
  await expect(page.getByTestId('demo-volume')).toHaveText('64 mm³');
  await expect(canvas).toBeVisible();
  const selectedUrl = page.url();
  const state = new URL(selectedUrl).searchParams.get('state');
  const data = await (await context.request.get(`${base}/api/demo?scenario=SC-01`)).json();
  const selected = data.timeline.items.find((p: { id: string }) => p.id === state);
  expect(selected.exact_value).toBe('64');
  expect(Object.keys(data.meshBindings)).toHaveLength(4);
  expect(data.meshBindings[state!]).toMatchObject({ point_id: selected.id, patient_id: selected.patient_id,
    branch_id: selected.branch_id, run_id: selected.run_id, state_ids: selected.state_ids, geometry_result_id: selected.geometry_result_id });
  expect(data.meshBindings[state!].surface_sha256).toMatch(/^[a-f0-9]{64}$/);
  await expect(canvas).toHaveAttribute('data-selected-annotation', state!);
  expect(JSON.parse((await canvas.getAttribute('data-world-bounds'))!)).toEqual({ min: data.meshes[state!].bounds_min_mm, max: data.meshes[state!].bounds_max_mm });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `${output}/02b-twin-followup.png`, fullPage: true });
  await page.reload();
  await expect(page.getByTestId('demo-volume')).toHaveText('64 mm³');
  await expect(canvas).toBeVisible();
  await timelineButtons.getByRole('button', { name: /Day 56/ }).click();
  await expect(page.getByTestId('demo-volume')).toHaveText('8 mm³');
  await page.goBack();
  await expect(page.getByTestId('demo-volume')).toHaveText('64 mm³');
  const verifiedFamilies: string[] = [];
  for (const [id, value] of [['SC-02', '216'], ['SC-03', '343'], ['SC-04', '64'], ['SC-05', '216']]) {
    await page.locator('#demo-scenario').selectOption(id);
    await expect(page.getByTestId('demo-volume')).toHaveText('216 mm³');
    await expect(canvas).toBeVisible();
    await page.getByRole('button', { name: 'Next state →', exact: true }).click();
    await expect(page.getByTestId('demo-volume')).toHaveText(`${value} mm³`);
    await expect(canvas).toBeVisible();
    verifiedFamilies.push(id);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `${output}/03-scenario-timeline.png`, fullPage: true });
  const nav = page.getByRole('navigation', { name: 'Demo workspace' });
  await nav.getByRole('link', { name: 'Clinical Data', exact: true }).click();
  await expect(page.getByRole('table', { name: 'Scenario observations with their actual relative times' })).toBeVisible();
  await expect(page.getByRole('img', { name: 'Synthetic region volume by relative day' })).toBeVisible();
  await expect(page.getByText(/No authentic laboratory, pathology or treatment records/)).toBeVisible();
  await page.screenshot({ path: `${output}/04-clinical.png`, fullPage: true });
  await nav.getByRole('link', { name: 'AI Research Insights', exact: true }).click();
  await expect(page.getByText('Live Meta AI: unavailable in this demo')).toBeVisible();
  await expect(page.getByText(/local template using the selected backend measurement/)).toBeVisible();
  await page.screenshot({ path: `${output}/05-insights.png`, fullPage: true });
  await nav.getByRole('link', { name: 'Hypothetical Scenarios', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Progressive growth', exact: true })).toBeVisible();
  await page.getByRole('link').filter({ has: page.getByRole('heading', { name: 'Progressive growth', exact: true }) }).click();
  await expect(canvas).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: `${output}/06-mobile.png`, fullPage: true });
  // Exercise actual WebGL context loss and recovery, retaining mask measurements.
  await canvas.evaluate(element => (element as HTMLCanvasElement).getContext('webgl2')!.getExtension('WEBGL_lose_context')!.loseContext());
  await expect(page.getByRole('button', { name: 'Retry 3D viewer' })).toBeVisible();
  await expect(page.getByTestId('demo-volume')).toHaveText('216 mm³');
  await page.getByRole('button', { name: 'Retry 3D viewer' }).click();
  await expect(canvas).toBeVisible();
  expect(backendRequests).toEqual([]);
  expect(errors).toEqual([]);
  writeFileSync(`${output}/browser-evidence.json`, JSON.stringify({ scope: 'Actual Chromium/WebGL over backend-prepared synthetic fixtures only', recorded_at: new Date().toISOString(),
    homepage: true, one_click_launch: true, manual_identifiers: false, webgl: true, camera_buttons: true, drag: true,
    state_measurement_mesh_link: true, prepared_mesh_bindings: true, refresh: true, browser_back: true, families: ['SC-01', ...verifiedFamilies], clinical_table: true,
    insights_mode: 'local template; live Meta unavailable', mobile_overflow: false, graphics_retry: true,
    browser_errors: errors, runtime_backend_requests: backendRequests }, null, 2));
});

test('demo boundaries: no session, cross-origin launch, unknown scope and unsupported writes', async ({ request }) => {
  expect((await request.get(`${base}/api/demo`)).status()).toBe(401);
  expect((await request.post(`${base}/api/demo-session`, { headers: { origin: 'https://untrusted.example' } })).status()).toBe(403);
  expect((await request.post(`${base}/api/demo-session`, { headers: { origin: base } })).status()).toBe(200);
  const catalog = await request.get(`${base}/api/demo`);
  expect(catalog.status()).toBe(200);
  expect(catalog.headers()['cache-control']).toContain('no-store');
  expect((await request.get(`${base}/api/demo?scenario=__proto__`)).status()).toBe(404);
  expect((await request.get(`${base}/api/demo?scenario=SC-01&project=other`)).status()).toBe(400);
  expect((await request.get(`${base}/api/demo?scenario=SC-01&scenario=SC-02`)).status()).toBe(400);
  expect((await request.post(`${base}/api/demo`, { data: { value: 1 } })).status()).toBe(405);
  const scenario = await (await request.get(`${base}/api/demo?scenario=SC-01`)).text();
  expect(scenario).not.toMatch(/Bearer |"token"|"mapping_id"|"object_key"|https?:\/\//);
});
