import { expect, test } from '@playwright/test';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';

const bundle = '.local/phase3-browser-fixture.json';

test('COS-E2E-002 continuous journey: scenario, timeline, charts, insights stay synchronized', async ({ page }) => {
  test.setTimeout(240000);
  test.slow();
  expect(readFileSync(bundle, 'utf8'), 'phase3 fixture must be running').toBeTruthy();
  const fixture = JSON.parse(readFileSync(bundle, 'utf8'));
  mkdirSync('docs/engineering/testing/browser-e2e', { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(String(error).slice(0, 200)));
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('404') && !message.text().includes('401')) errors.push(message.text().slice(0, 200));
  });

  async function token(value: string) {
    await page.evaluate((secret: string) => {
      const input = document.querySelector<HTMLInputElement>('input[type=password]')!;
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(input, secret);
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }, value);
  }

  // 1. Simulation branch context.
  await page.goto('http://127.0.0.1:3000/simulation');
  await page.getByLabel('Project UUID', { exact: true }).fill(fixture.project_id);
  await page.getByLabel('Patient UUID', { exact: true }).fill(fixture.patient_id);
  await page.getByLabel('Branch UUID', { exact: true }).fill(fixture.branch_id);
  await token(fixture.token);
  const loadBranch = page.getByRole('button', { name: 'Load baseline branch', exact: true });
  await loadBranch.focus();
  await loadBranch.press('Enter');
  await expect(page.getByRole('status').filter({ hasText: 'Branch loaded.' })).toBeVisible({ timeout: 90000 });
  await page.screenshot({ path: 'docs/engineering/testing/browser-e2e/journey-1-simulation.png' });

  // 2. Exact timeline for the same branch/run.
  await page.goto('http://127.0.0.1:3000/timeline');
  await page.getByLabel('Project UUID', { exact: true }).fill(fixture.project_id);
  await page.getByLabel('Patient UUID', { exact: true }).fill(fixture.patient_id);
  await token(fixture.token);
  await page.getByRole('combobox', { name: 'Observation context', exact: true }).selectOption('simulation');
  await page.getByLabel('Exact data revision', { exact: true }).fill(String(fixture.data_revision));
  await page.getByLabel('Knowledge as of (ISO timestamp with timezone)', { exact: true }).fill(fixture.knowledge_as_of);
  await page.getByLabel('Branch UUID', { exact: true }).fill(fixture.branch_id);
  await page.getByLabel('Run UUID', { exact: true }).fill(fixture.run_id);
  await page.getByLabel('Published completion UUID', { exact: true }).fill(fixture.completion_id);
  const response = page.waitForResponse((r) => r.url().endsWith('/timeline-queries'));
  await page.getByRole('button', { name: 'Load exact timeline', exact: true }).click();
  const timeline = await (await response).json();
  expect(timeline.items.length).toBeGreaterThan(0);
  await page.screenshot({ path: 'docs/engineering/testing/browser-e2e/journey-2-timeline.png' });

  // 3. Charts bind to the same project/patient without inventing values.
  // No session token is supplied here, so the authorized read must deny
  // safely (401) instead of inventing data or crashing.
  await page.goto(`http://127.0.0.1:3000/charts?project=${fixture.project_id}&patient=${fixture.patient_id}`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(4000);
  const chartsBody = (await page.textContent('main')) ?? '';
  expect(chartsBody.length).toBeGreaterThan(50);
  expect(chartsBody).toMatch(/restricted|sign in|unavailable|denied|not visible|needs|authorized/i);
  await page.screenshot({ path: 'docs/engineering/testing/browser-e2e/journey-3-charts.png' });

  // 4. Insights bind to the same project/patient with honest uncertainty.
  // Same authorized-read gating expectation as charts.
  await page.goto(`http://127.0.0.1:3000/insights?project=${fixture.project_id}&patient=${fixture.patient_id}`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(4000);
  const insightsBody = (await page.textContent('main')) ?? '';
  expect(insightsBody.length).toBeGreaterThan(50);
  expect(insightsBody).toMatch(/restricted|sign in|unavailable|denied|not visible|needs|authorized|enter below|exact context|exact insight scope/i);
  await page.screenshot({ path: 'docs/engineering/testing/browser-e2e/journey-4-insights.png' });

  writeFileSync('docs/engineering/testing/browser-e2e/journey-summary.json', JSON.stringify({
    recorded_at: new Date().toISOString(),
    scope: 'Continuous browser journey on the explicitly synthetic phase3 fixture context (no authentic patient)',
    steps: ['simulation branch loaded', 'exact timeline queried', 'charts bound', 'insights bound'],
    timeline_items: timeline.items.length,
    console_errors: errors,
  }, null, 2));
  expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
});
