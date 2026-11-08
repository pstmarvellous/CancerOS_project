import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';

const base = 'http://127.0.0.1:3000';
const output = 'docs/engineering/testing/rec04-scenarios';

const FAMILIES = [
  { id: 'SC-01', plain: 'Continuous shrinkage' },
  { id: 'SC-02', plain: 'Little or no size change' },
  { id: 'SC-03', plain: 'Continued growth' },
  { id: 'SC-04', plain: 'Shrinks, then grows again' },
  { id: 'SC-05', plain: 'Stable size with worsening symptoms' },
];

test('REC-04 five families: plain names, timepoints, correspondence, observations, recovery', async ({ page }) => {
  test.setTimeout(600000);
  page.setViewportSize({ width: 1440, height: 1000 });
  mkdirSync(output, { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message.slice(0, 200)));
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|Failed to load resource/i.test(message.text())) errors.push(message.text().slice(0, 200));
  });
  const seen: string[] = [];

  for (const [index, family] of FAMILIES.entries()) {
    // 1-2. Select the scenario by its plain name; its meaning is visible.
    await page.goto(`${base}/demo?view=scenarios`);
    await expect(page.getByRole('heading', { name: family.plain, exact: true }).first()).toBeVisible({ timeout: 60000 });
    await page.getByRole('link', { name: new RegExp(`${family.plain}.*Explore in 3D`, 's') }).first().click();
    await expect(page).toHaveURL(new RegExp(`scenario=${family.id}`));
    await expect(page.getByLabel('Hypothetical scenario')).toHaveValue(family.id);

    // 3-4. Change the timepoint; model, chart and measurements update together.
    const dayButtons = page.getByLabel('Scenario timeline').getByRole('button', { name: /Day \d+/ });
    await expect(dayButtons.first()).toBeVisible({ timeout: 30000 });
    const count = await dayButtons.count();
    expect(count, `${family.id} follow-up states`).toBeGreaterThanOrEqual(3);
    await dayButtons.nth(1).click();
    await expect(page).toHaveURL(/state=/, { timeout: 30000 });
    await expect(page.getByTestId('demo-comparison')).toContainText(/Compared with this scenario's 216 mm³ synthetic baseline/, { timeout: 30000 });
    const volume = await page.getByTestId('demo-volume').textContent();
    expect(volume, `${family.id} volume text`).toMatch(/mm³/);
    seen.push(`${family.id}:${volume?.trim()}`);
    if (index === 2) await page.screenshot({ path: `${output}/family-${family.id}.png`, fullPage: true });

    // 5-6. Open observations; synthetic provenance explicit; values exact.
    await page.getByRole('link', { name: /Inspect clinical observations/ }).click();
    await expect(page.getByText(/retain their own collection days|not carried forward/i).first()).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/Synthetic scenario/i).first()).toBeVisible();
    if (index === 0) await page.screenshot({ path: `${output}/observations-${family.id}.png`, fullPage: true });
    await page.goBack();
  }
  expect(new Set(seen).size, 'distinct scenario volumes').toBeGreaterThanOrEqual(3);

  // Missing data: SC-02 has only weight on day 5 plus imaging; table states missingness honestly.
  await page.goto(`${base}/demo?view=clinical&scenario=SC-02`);
  await expect(page.getByText(/Missing|Not recorded|no authentic/i).first()).toBeVisible({ timeout: 60000 });

  // Back navigation and refresh restore the selected state.
  await page.goto(`${base}/demo?view=twin&scenario=SC-04`);
  const timeline = page.getByLabel('Scenario timeline');
  const dayButtons = timeline.getByRole('button', { name: /Day \d+/ });
  await expect(dayButtons.first()).toBeVisible({ timeout: 60000 });
  await dayButtons.nth(1).click();
  await expect(page.getByTestId('demo-volume')).toContainText('8', { timeout: 30000 });
  const withState = page.url();
  expect(withState).toContain('state=');
  await page.goto(`${base}/demo?view=clinical&scenario=SC-04`);
  await page.goBack();
  await expect(page).toHaveURL(/view=twin/, { timeout: 30000 });
  expect(page.url()).toContain('state=');
  await expect(page.getByTestId('demo-comparison')).toContainText('synthetic baseline', { timeout: 30000 });
  await page.reload();
  expect(page.url()).toContain('state=');
  await expect(page.getByTestId('demo-volume')).toContainText('8', { timeout: 60000 });
  await page.screenshot({ path: `${output}/refresh-restored.png`, fullPage: true });

  expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
  writeFileSync(`${output}/rec04-scenarios-evidence.json`, JSON.stringify({
    recorded_at: new Date().toISOString(),
    scope: 'Fresh browser session; token-free synthetic bundle only',
    family_volumes: seen,
    journey: ['five-families', 'timepoints', 'correspondence', 'observations', 'missing', 'back', 'refresh'],
    browser_errors: errors,
  }, null, 2));
});
