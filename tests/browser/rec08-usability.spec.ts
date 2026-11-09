import { expect, test, type Locator, type Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const base = process.env.CANCEROS_BROWSER_BASE_URL ?? 'http://127.0.0.1:3001';
const output = process.env.CANCEROS_BROWSER_EVIDENCE_DIR ?? 'docs/engineering/testing/rec06-09-audit/usability';
const viewports = [{ width: 1440, height: 900 }, { width: 390, height: 844 }, { width: 320, height: 740 }];

async function auditViewport(page: Page, tag: string) {
  const measurements = [];
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    const result = await page.evaluate(() => {
      const controls = [...document.querySelectorAll<HTMLElement>('button, a[href], input:not([type=hidden]), select, textarea, summary')]
        .filter(element => element.checkVisibility() && element.getBoundingClientRect().width > 0)
        .map(element => {
          const box = element.getBoundingClientRect();
          return { name: element.getAttribute('aria-label') ?? element.textContent?.trim().slice(0, 80) ?? element.tagName,
            x: box.x, y: box.y, right: box.right, bottom: box.bottom, width: box.width, height: box.height };
        });
      const overlaps: string[] = [];
      for (let i = 0; i < controls.length; i++) for (let j = i + 1; j < controls.length; j++) {
        const a = controls[i], b = controls[j];
        if (a.x < b.right - 1 && b.x < a.right - 1 && a.y < b.bottom - 1 && b.y < a.bottom - 1) overlaps.push(`${a.name} / ${b.name}`);
      }
      return { overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        controlCount: controls.length, overlaps,
        clipped: controls.filter(box => box.x < -1 || box.right > innerWidth + 1).map(box => box.name) };
    });
    const screenshot = `${tag}-${viewport.width}.png`;
    await page.screenshot({ path: `${output}/${screenshot}`, fullPage: true });
    measurements.push({ ...viewport, ...result, screenshot });
    writeFileSync(`${output}/${tag}.json`, JSON.stringify({ scope: 'Actual browser layout, synthetic data only', measurements }, null, 2));
    expect.soft(result.overflow, `${tag} horizontal overflow at ${viewport.width}px`).toBeLessThanOrEqual(1);
    expect.soft(result.clipped, `${tag} horizontally clipped controls at ${viewport.width}px`).toEqual([]);
    expect.soft(result.overlaps, `${tag} overlapping controls at ${viewport.width}px`).toEqual([]);
    expect(result.controlCount, `${tag} must expose real controls`).toBeGreaterThan(0);
  }
}

async function tabTo(page: Page, control: Locator) {
  await expect(control).toBeVisible();
  for (let step = 0; step < 180; step++) {
    if (await control.evaluate(element => document.activeElement === element)) {
      expect(await control.evaluate(element => element.matches(':focus-visible'))).toBe(true);
      return;
    }
    await page.keyboard.press('Tab');
  }
  throw new Error(`Core action cannot be reached by Tab: ${await control.getAttribute('aria-label') ?? await control.textContent()}`);
}

test('REC-08 all public screens fit desktop, 390 and 320px widths', async ({ page }) => {
  test.setTimeout(360000);
  mkdirSync(output, { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base);
  await expect(page.getByRole('link', { name: 'Explore Interactive Demo', exact: true })).toBeVisible();
  await auditViewport(page, '01-home');
  await page.getByRole('link', { name: 'Explore Interactive Demo', exact: true }).click();
  await expect(page.locator('canvas[data-render-ready=true]')).toBeVisible({ timeout: 60000 });
  for (const [view, tag] of [['twin', '04-twin'], ['clinical', '05-clinical'], ['scenarios', '06-scenarios'], ['insights', '07-insights'], ['technical', '08-technical']]) {
    await page.goto(`${base}/demo?view=${view}&scenario=SC-01`);
    await expect(page.locator('#demo-scenario')).toBeVisible();
    if (view === 'twin') await expect(page.locator('canvas[data-render-ready=true]')).toBeVisible({ timeout: 60000 });
    else await expect(page.getByRole('heading', { level: 2 }).first()).toBeVisible();
    await auditViewport(page, tag);
  }
  expect(errors).toEqual([]);
});

test('REC-08 keyboard operates launch, camera, scenario, time and maximized viewer', async ({ page }) => {
  test.setTimeout(240000);
  await page.goto(base);
  await tabTo(page, page.getByRole('link', { name: 'Explore Interactive Demo', exact: true }));
  await page.keyboard.press('Enter');
  const canvas = page.locator('canvas[data-render-ready=true]');
  await expect(canvas).toBeVisible({ timeout: 60000 });
  const selector = page.locator('#demo-scenario');
  await tabTo(page, selector);
  await page.keyboard.press('Home');
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Tab');
  await expect(selector).toHaveValue('SC-02');
  await expect(canvas).toBeVisible({ timeout: 60000 });
  const scenarioResponse = await page.request.get(`${base}/api/demo?scenario=SC-02`);
  expect(scenarioResponse.ok()).toBe(true);
  const scenario = await scenarioResponse.json() as { timeline: { items: { id: string; measurement_basis: string; time: { reference: { value: string } }; exact_value: string }[] } };
  const followup = scenario.timeline.items.filter(point => ['baseline_reference', 'mask_realized'].includes(point.measurement_basis))[1];
  await tabTo(page, page.getByText('More camera controls', { exact: true }));
  await page.keyboard.press('Enter');
  const rotate = page.getByRole('button', { name: 'Rotate left', exact: true });
  await tabTo(page, rotate);
  const before = await canvas.getAttribute('data-camera-state');
  await page.keyboard.press('Enter');
  await expect(canvas).not.toHaveAttribute('data-camera-state', before!);
  await tabTo(page, page.getByRole('button', { name: 'Next state →', exact: true }));
  await page.keyboard.press('Enter');
  const selectedDay = page.getByLabel('Scenario timeline', { exact: true }).getByRole('button', { name: /Day /, pressed: true });
  await expect(selectedDay).toHaveCount(1);
  await expect(selectedDay).toContainText(`Day ${followup.time.reference.value}`);
  await expect(page.locator('figure').getByRole('button', { name: `Day ${followup.time.reference.value}: ${followup.exact_value} mm³`, pressed: true, exact: true })).toHaveCount(1);
  await expect(page.getByTestId('demo-volume')).toHaveText(`${followup.exact_value} mm³`);
  expect(new URL(page.url()).searchParams.get('state')).toBe(followup.id);
  const maximize = page.getByRole('button', { name: 'Maximize viewer', exact: true });
  await tabTo(page, maximize);
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog', { name: 'Selected digital twin' });
  await expect(dialog).toBeVisible();
  await page.keyboard.press('Tab');
  expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Shift+Tab');
  expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
  expect(await dialog.evaluate(element => {
    const controls = [...element.querySelectorAll('button:not(:disabled), select, a[href], [tabindex="0"], summary')].filter(item => item.checkVisibility());
    return document.activeElement === controls.at(-1);
  })).toBe(true);
  await page.keyboard.press('Tab');
  expect(await dialog.evaluate(element => {
    const controls = [...element.querySelectorAll('button:not(:disabled), select, a[href], [tabindex="0"], summary')].filter(item => item.checkVisibility());
    return document.activeElement === controls[0];
  })).toBe(true);
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(maximize).toBeFocused();
});

test('REC-08 authorized library, creation and clinical form fit all widths', async ({ page }) => {
  test.setTimeout(360000);
  mkdirSync(output, { recursive: true });
  const fixture = JSON.parse(readFileSync('.local/product-browser-fixture.json', 'utf8')) as { admin_token: string; synthetic_only: boolean };
  expect(fixture.synthetic_only).toBe(true);
  await page.goto(`${base}/cases`);
  await page.getByLabel('Research access token').fill(fixture.admin_token);
  await page.getByRole('button', { name: 'Sign in to research workspace' }).click();
  const newCase = page.getByRole('button', { name: 'New research case', exact: true });
  await expect(newCase).toBeVisible({ timeout: 30000 });
  await auditViewport(page, '02-research-cases');
  await tabTo(page, newCase);
  await page.keyboard.press('Enter');
  const form = page.getByRole('form', { name: 'Create research case' });
  await expect(form).toBeVisible();
  await auditViewport(page, '03-case-creation');
  const unique = `USABILITY-${Date.now()}`;
  await form.getByLabel(/Case title/).fill('Usability audit artificial case');
  await form.getByLabel(/Case reference/).fill(unique);
  await form.getByLabel(/Participant code/).fill(unique);
  await form.getByLabel(/Source reference/).fill('Artificial usability audit source');
  await tabTo(page, form.getByRole('button', { name: 'Create Case', exact: true }));
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/cases\/detail\?/);
  const clinical = page.getByRole('tab', { name: /Clinical Records/ });
  await tabTo(page, clinical);
  await page.keyboard.press('Enter');
  const observation = page.getByRole('form', { name: 'Save clinical observation' });
  await expect(observation).toBeVisible({ timeout: 30000 });
  await auditViewport(page, '09-authorized-clinical');
  const labels = await observation.locator('input, select, textarea').evaluateAll(elements => elements.map(element => element.getAttribute('placeholder') ?? element.getAttribute('aria-label') ?? ''));
  expect(labels.filter(label => /uuid/i.test(label))).toEqual([]);
  await tabTo(page, observation.getByRole('button', { name: 'Save observation', exact: true }));
  await expect(observation.getByRole('button', { name: 'Save observation', exact: true })).toBeFocused();
});
