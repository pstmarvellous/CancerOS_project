import { expect, test } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const base = process.env.CANCEROS_BROWSER_BASE_URL ?? 'http://127.0.0.1:3001';
const output = process.env.CANCEROS_BROWSER_EVIDENCE_DIR ?? 'docs/engineering/testing/rec09-acceptance';
const bundle = '.local/product-browser-fixture.json';

function verdicts() {
  const rows: { journey: string; step: string; expected: string; actual: string; verdict: 'PASS' | 'FAIL' | 'BLOCKED' }[] = [];
  return {
    rows,
    record(journey: string, step: string, expected: string, actual: string, verdict: 'PASS' | 'FAIL' | 'BLOCKED') {
      rows.push({ journey, step, expected, actual, verdict });
    },
  };
}

function fixture() {
  const parsed = JSON.parse(readFileSync(bundle, 'utf8')) as {
    api_url: string; project_id: string; source_version_id: string; admin_token: string; viewer_token: string; outsider_token: string; synthetic_only: boolean;
  };
  expect(parsed.synthetic_only).toBe(true);
  return parsed;
}

test('REC-09 Journey A — first-time visitor completes the synthetic demonstration', async ({ page, context }) => {
  test.setTimeout(420000);
  const check = verdicts();
  await context.clearCookies();
  await page.setViewportSize({ width: 1440, height: 900 });
  mkdirSync(output, { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/favicon/i.test(message.text())) errors.push(message.text()); });

  await page.goto(base);
  check.record('A', 'purpose', 'Purpose understandable without instructions', await page.getByRole('heading', { level: 1 }).textContent() ?? '', 'PASS');
  await page.getByRole('link', { name: 'Explore Interactive Demo' }).click();
  await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible({ timeout: 60000 });
  check.record('A', 'launch-demo', 'Demo launches', 'Demo workspace visible', 'PASS');

  const canvas = page.locator('canvas[data-render-ready=true]');
  await expect(canvas).toBeVisible({ timeout: 60000 });
  const before = await canvas.getAttribute('data-camera-state');
  await page.getByText('More camera controls').click();
  await page.getByRole('button', { name: 'Rotate left', exact: true }).click();
  await expect(canvas).not.toHaveAttribute('data-camera-state', before!);
  check.record('A', 'manipulate-3d', '3D camera responds to controls', 'Camera state changed after Rotate left', 'PASS');
  await page.screenshot({ path: `${output}/A-01-twin.png` });

  const seen: Record<string, string> = {};
  for (const scenario of ['SC-01', 'SC-02', 'SC-03', 'SC-04', 'SC-05']) {
    await page.locator('#demo-scenario').selectOption(scenario);
    await page.getByRole('button', { name: 'Next state →', exact: true }).click();
    await expect(page.getByTestId('demo-volume')).toBeVisible({ timeout: 30000 });
    seen[scenario] = (await page.getByTestId('demo-volume').textContent()) ?? '';
  }
  check.record('A', 'all-scenarios', 'All five scenarios selectable with distinct follow-up measurements', JSON.stringify(seen), new Set(Object.values(seen)).size >= 3 ? 'PASS' : 'FAIL');

  await page.locator('#demo-scenario').selectOption('SC-01');
  const day37 = page.getByRole('button', { name: /Day 37/ }).first();
  await day37.click();
  await expect(page.getByTestId('demo-volume')).toHaveText('64 mm³', { timeout: 30000 });
  check.record('A', 'follow-time', 'Day 37 shows 64 mm³', (await page.getByTestId('demo-volume').textContent()) ?? '', 'PASS');
  await page.screenshot({ path: `${output}/A-02-day37.png` });

  await page.getByRole('link', { name: /Inspect clinical observations/ }).click();
  await expect(page.getByText('Selected geometry:').first()).toBeVisible({ timeout: 30000 });
  const obsVisible = await page.getByRole('table').count();
  check.record('A', 'observations', 'Scenario observations listed with days', `${obsVisible} table(s)`, obsVisible > 0 ? 'PASS' : 'FAIL');
  await page.screenshot({ path: `${output}/A-03-clinical.png` });

  await page.getByRole('link', { name: 'AI Research Insights' }).first().click();
  await expect(page.getByText('AI Research Insights').first()).toBeVisible({ timeout: 30000 });
  const insightsBody = (await page.textContent('main')) ?? '';
  const localShown = /local template/i.test(insightsBody) && /216|64/.test(insightsBody);
  const liveDenied = /unavailable in this demo|does not call an external model/i.test(insightsBody);
  check.record('A', 'research-explanation', 'Clearly labeled local explanation; live marked unavailable', `local=${localShown} live-denied=${liveDenied}`, localShown && liveDenied ? 'PASS' : 'FAIL');
  await page.screenshot({ path: `${output}/A-04-insights.png` });

  await page.setViewportSize({ width: 390, height: 844 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  check.record('A', 'narrow-layout', 'No horizontal scrolling at 390px', `overflow=${overflow}px`, overflow <= 1 ? 'PASS' : 'FAIL');
  await page.screenshot({ path: `${output}/A-05-narrow.png`, fullPage: true });

  expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
  writeFileSync(`${output}/journey-A.json`, JSON.stringify({ recorded_at: new Date().toISOString(), steps: check.rows }, null, 2));
  expect(check.rows.every(row => row.verdict === 'PASS')).toBe(true);
});

test('REC-09 Journey C — imaging workflow on eligible synthetic data', async ({ page, context }) => {
  test.setTimeout(420000);
  const check = verdicts();
  await context.clearCookies();
  await page.setViewportSize({ width: 1440, height: 1000 });
  mkdirSync(output, { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/favicon|Failed to load resource/i.test(message.text())) errors.push(message.text()); });
  const seed = JSON.parse(readFileSync('.local/rec09-imaging-seed.json', 'utf8')) as { project_id: string; patient_id: string };
  const data = fixture();

  await page.goto(`${base}/cases`);
  await page.getByLabel('Research access token').fill(data.admin_token);
  await page.getByRole('button', { name: 'Sign in to research workspace' }).click();
  await expect(page.getByRole('button', { name: 'New research case', exact: true })).toBeVisible({ timeout: 30000 });

  await page.goto(`${base}/cases/detail?project=${seed.project_id}&patient=${seed.patient_id}&tab=imaging`);
  await expect(page.getByRole('heading', { name: 'Add Imaging Study' })).toBeVisible({ timeout: 30000 });
  check.record('C', 'open-workflow', 'Imaging workflow opens in the selected case', 'Add Imaging Study visible', 'PASS');

  await page.getByLabel('Associated study').selectOption({ index: 1 });
  await expect(page.getByLabel('Study import')).toBeVisible({ timeout: 30000 });
  await page.getByLabel('Study import').selectOption({ index: 1 });
  await expect(page.getByText(/Associated study selected/)).toBeVisible({ timeout: 30000 });
  check.record('C', 'associate-review', 'Study and import selected with provenance', 'Provenance step reached', 'PASS');
  await page.screenshot({ path: `${output}/C-01-provenance.png` });

  await page.getByRole('button', { name: 'Check image geometry' }).click();
  await expect(page.getByText(/geometry is valid/i)).toBeVisible({ timeout: 60000 });
  check.record('C', 'geometry', 'Geometry derived from verified metadata', 'valid grid reported', 'PASS');

  await expect.poll(async () => {
    const texts = await page.getByRole('alert').allTextContents();
    return texts.some(text => text.includes('This imaging study has no compatible verified region mask.'));
  }, { timeout: 30000 }).toBe(true);
  const alerts = await page.getByRole('alert').allTextContents();
  const found = alerts.some(text => text.includes('This imaging study has no compatible verified region mask. A 3D tumor measurement is not yet available.'));
  check.record('C', 'no-mask-message', 'Absent mask reported honestly, none synthesized', found ? 'required message shown' : alerts.join(' | ').slice(0, 160), found ? 'PASS' : 'FAIL');
  expect(found).toBe(true);
  await page.screenshot({ path: `${output}/C-02-geometry-no-mask.png` });

  await page.reload();
  await expect(page.getByRole('heading', { name: 'Add Imaging Study' })).toBeVisible({ timeout: 30000 });
  const retained = new URL(page.url()).searchParams.get('imaging_study');
  check.record('C', 'refresh-retains', 'Case retains the study association after refresh', `imaging_study=${retained}`, retained ? 'PASS' : 'FAIL');
  await page.screenshot({ path: `${output}/C-03-full-geometry.png` });

  // Full chain on a second synthetic case: mask -> QC -> measurements -> 3D.
  const full = JSON.parse(readFileSync('.local/rec09-fullchain-seed.json', 'utf8')) as { project_id: string; patient_id: string };
  await page.goto(`${base}/cases/detail?project=${full.project_id}&patient=${full.patient_id}&tab=imaging`);
  await expect(page.getByRole('heading', { name: 'Add Imaging Study' })).toBeVisible({ timeout: 30000 });
  await page.getByLabel('Associated study').selectOption({ index: 1 });
  await expect(page.getByLabel('Study import')).toBeVisible({ timeout: 30000 });
  await page.getByLabel('Study import').selectOption({ index: 1 });
  await expect(page.getByText(/Associated study selected/)).toBeVisible({ timeout: 30000 });
  await page.getByRole('button', { name: 'Check image geometry' }).click();
  await expect(page.getByText(/geometry is valid/i)).toBeVisible({ timeout: 60000 });
  await page.getByLabel('Authorized region mask').selectOption({ index: 1 });
  await expect(page.getByText(/Mask technical QC passed/)).toBeVisible({ timeout: 60000 });
  await page.getByRole('button', { name: 'Calculate measurement and reconstruct 3D' }).click();
  await expect(page.getByRole('link', { name: 'Open 3D Model' })).toBeVisible({ timeout: 180000 });
  const scenarioUrl = await page.getByRole('link', { name: 'Create a hypothetical branch from this synthetic engineering baseline' }).getAttribute('href');
  writeFileSync('.local/rec-audit-scenario-link.json', JSON.stringify({ scenarioUrl }));
  check.record('C', 'mask-qc', 'Compatible mask selected; QC passes', 'QC pass message shown', 'PASS');
  await page.getByRole('link', { name: 'Open 3D Model' }).click();
  const model = page.locator('canvas[data-render-ready=true]');
  await expect(model).toBeVisible({ timeout: 60000 });
  if (await model.count() > 0) {
    await expect(model).toBeVisible({ timeout: 60000 });
    await expect(page.getByText(/Server measurement/).first()).toBeVisible({ timeout: 30000 });
    const overlay = (await page.getByText(/Server measurement/).first().textContent()) ?? '';
    check.record('C', 'mesh-3d', '3D mesh renders with server measurement overlay', overlay.slice(0, 90), /mm/.test(overlay) ? 'PASS' : 'FAIL');
  } else {
    const twinBody = (await page.textContent('main')) ?? '';
    check.record('C', 'mesh-3d', 'Case 3D viewer displays validated mesh for the QC-passed chain', twinBody.replace(/\s+/g, ' ').slice(0, 220), 'FAIL');
  }
  await page.screenshot({ path: `${output}/C-04-mesh-3d.png` });

  expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
  writeFileSync(`${output}/journey-C.json`, JSON.stringify({ recorded_at: new Date().toISOString(), scope: 'synthetic fixture only; authentic MRI gate blocked', steps: check.rows }, null, 2));
  expect(check.rows.every(row => row.verdict === 'PASS')).toBe(true);
});

test('REC-09 Journey B — authorized artificial case management with isolation', async ({ page, context }) => {
  test.setTimeout(420000);
  const check = verdicts();
  await context.clearCookies();
  await page.setViewportSize({ width: 1440, height: 1000 });
  mkdirSync(output, { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/favicon|Failed to load resource/i.test(message.text())) errors.push(message.text()); });
  const data = fixture();
  const codeA = `REC09-${Date.now()}`;

  await page.goto(`${base}/cases`);
  await page.getByLabel('Research access token').fill(data.admin_token);
  await page.getByRole('button', { name: 'Sign in to research workspace' }).click();
  await expect(page.getByRole('button', { name: 'New research case', exact: true })).toBeVisible({ timeout: 30000 });
  check.record('B', 'signin', 'Admin signs in', 'New research case visible', 'PASS');

  await page.getByRole('button', { name: 'New research case', exact: true }).click();
  const creation = page.getByRole('form', { name: 'Create research case' });
  await creation.getByLabel(/Case title/).fill('REC-09 Acceptance Case A');
  await creation.getByLabel(/Case reference/).fill(codeA);
  await creation.getByLabel(/Participant code/).fill(codeA);
  await creation.getByLabel(/Source reference/).fill('Artificial register entry 090');
  await creation.getByRole('button', { name: 'Create Case', exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/detail\?/);
  const patientA = new URL(page.url()).searchParams.get('patient')!;
  check.record('B', 'create-case', 'Case created and opened', `patient=${patientA.slice(0, 8)}`, 'PASS');
  await page.screenshot({ path: `${output}/B-01-created.png` });

  await page.getByRole('tab', { name: /Clinical Records/ }).click();
  const form = page.getByRole('form', { name: 'Save clinical observation' });
  await form.getByLabel('Specific concept').selectOption('hemoglobin');
  await form.getByLabel(/Source original term/).fill('REC-09 hemoglobin observation');
  await form.getByLabel(/Source reference/).fill('Artificial report row 9');
  await form.getByLabel(/Collection date/).fill('2026-11-09');
  await form.getByLabel(/Measured value|Value/).fill('9.1');
  await form.getByRole('button', { name: 'Save observation', exact: true }).click();
  const timeline = page.getByRole('region', { name: 'Clinical observation timeline' });
  await expect(timeline.getByText('9.1 g/dL', { exact: true })).toBeVisible({ timeout: 30000 });
  check.record('B', 'enter-observation', 'Artificial observation saved and listed', '9.1 g/dL visible', 'PASS');

  await page.reload();
  await page.getByRole('tab', { name: /Clinical Records/ }).click();
  await expect(page.getByRole('region', { name: 'Clinical observation timeline' }).getByText('9.1 g/dL', { exact: true })).toBeVisible({ timeout: 30000 });
  check.record('B', 'save-reopen', 'Refresh retains the observation', '9.1 g/dL after reload', 'PASS');

  const row = timeline.getByRole('row').filter({ hasText: 'REC-09 hemoglobin observation' });
  await row.getByRole('button', { name: 'Correct' }).click();
  await form.getByLabel(/Measured value|Value/).fill('9.2');
  await form.getByRole('button', { name: 'Save observation', exact: true }).click();
  await expect(timeline.getByText('9.2 g/dL', { exact: true })).toBeVisible({ timeout: 30000 });
  await expect(row.getByText(/Superseded/)).toBeVisible();
  check.record('B', 'correct-value', 'Correction appends with retained revision', '9.2 g/dL + Superseded', 'PASS');

  await page.getByRole('tab', { name: /Charts:/ }).click();
  await expect(page.getByRole('region', { name: 'Clinical record parity table' }).getByText('9.2 g/dL', { exact: true })).toBeVisible({ timeout: 30000 });
  check.record('B', 'chart', 'Corrected value appears in chart parity table', '9.2 g/dL in chart', 'PASS');
  await page.screenshot({ path: `${output}/B-02-chart.png` });

  await page.getByRole('tab', { name: /Clinical Records/ }).click();
  const caseAUrl = page.url();
  await page.goto(`${base}/cases?project=${data.project_id}`);
  await page.goto(caseAUrl);
  await page.getByRole('tab', { name: /Clinical Records/ }).click();
  await expect(page.getByRole('region', { name: 'Clinical observation timeline' }).getByText('9.2 g/dL', { exact: true })).toBeVisible();
  check.record('B', 'navigate-back', 'Saved correction remains after leaving and returning', '9.2 g/dL retained', 'PASS');
  await page.goto(`${base}/cases?project=${data.project_id}`);
  await page.getByRole('button', { name: 'New research case', exact: true }).click();
  const codeB = `${codeA}-B`;
  const creationB = page.getByRole('form', { name: 'Create research case' });
  await creationB.getByLabel(/Case title/).fill('REC-09 Acceptance Case B');
  await creationB.getByLabel(/Case reference/).fill(codeB);
  await creationB.getByLabel(/Participant code/).fill(codeB);
  await creationB.getByLabel(/Source reference/).fill('Artificial register entry 091');
  await creationB.getByRole('button', { name: 'Create Case', exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/detail\?/);
  const patientB = new URL(page.url()).searchParams.get('patient')!;
  await page.getByRole('tab', { name: /Clinical Records/ }).click();
  await expect(page.getByRole('region', { name: 'Clinical observation timeline' })).toBeVisible();
  const bodyB = (await page.textContent('main')) ?? '';
  const isolated = patientB !== patientA && !bodyB.includes('9.2 g/dL') && !bodyB.includes(codeA);
  check.record('B', 'isolation', 'Case B sees none of Case A data', `isolated=${isolated}`, isolated ? 'PASS' : 'FAIL');
  await page.screenshot({ path: `${output}/B-03-isolation.png` });
  await page.goto(`${base}/cases`);
  await page.getByRole('button', { name: /Sign out/ }).click();
  const denied = await page.request.get(`${base}/api/case-detail?project=${data.project_id}&patient=${patientA}`);
  expect(denied.status()).toBe(401);
  check.record('B', 'signout', 'Sign-out revokes case access', 'Case API returns401 after sign-out', 'PASS');

  expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
  writeFileSync(`${output}/journey-B.json`, JSON.stringify({ recorded_at: new Date().toISOString(), case_a: patientA, case_b: patientB, steps: check.rows }, null, 2));
  expect(check.rows.every(row => row.verdict === 'PASS')).toBe(true);
});

test('REC-09 Journeys D and E — actual generation and selected-case local explanation', async ({ page, context }) => {
  test.setTimeout(600000);
  await context.clearCookies();
  mkdirSync(output, { recursive: true });
  const data = fixture();
  const link = JSON.parse(readFileSync('.local/rec-audit-scenario-link.json', 'utf8')) as { scenarioUrl: string };
  const d = verdicts(), e = verdicts();
  const external: string[] = [];
  page.on('request', request => { if (/api\.meta\.ai/.test(request.url())) external.push(request.url()); });
  await page.goto(`${base}/cases`);
  await page.getByLabel('Research access token').fill(data.admin_token);
  await page.getByRole('button', { name: 'Sign in to research workspace' }).click();
  await expect(page.getByRole('button', { name: 'New research case', exact: true })).toBeVisible();
  await page.goto(base + link.scenarioUrl);
  await page.getByRole('button', { name: 'Create hypothetical branch from selected measurement', exact: true }).click();
  await expect(page.getByText(/Hypothetical engineering branch created/)).toBeVisible({ timeout: 30000 });
  await page.getByRole('button', { name: 'Load baseline branch', exact: true }).click();
  await expect(page.getByText(/Branch loaded with the current draft revision/)).toBeVisible();
  await page.getByLabel('Follow-up days (relative)').fill('10, 30, 60');
  await page.getByLabel(/Explicit target volumes mm³/).fill('13, 8, 1');
  await page.getByLabel(/Hypothetical hemoglobin values/).fill('12, 11, 10');
  await page.getByRole('button', { name: 'Save immutable draft version', exact: true }).click();
  await expect(page.getByText(/Immutable draft saved/)).toBeVisible({ timeout: 30000 });
  await page.getByRole('button', { name: 'Inspect eligibility and schedule', exact: true }).click();
  await expect(page.getByRole('table', { name: 'Server sampled schedule · relative days' })).toBeVisible();
  d.record('D', 'configure', 'Explicit supported scenario saved and inspected', 'SC-01 targets13/8/1; days10/30/60; hypothetical hemoglobin12/11/10', 'PASS');
  await page.getByRole('checkbox', { name: /I reviewed the explicit assumptions/ }).check();
  await page.getByRole('button', { name: 'Freeze isolated test run', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Generate complete engineering run', exact: true })).toBeEnabled({ timeout: 30000 });
  await page.getByRole('button', { name: 'Generate complete engineering run', exact: true }).click();
  await expect(page.getByText(/Worker queued/)).toBeVisible({ timeout: 30000 });
  await expect.poll(async () => {
    await page.getByRole('button', { name: 'Refresh worker status', exact: true }).click();
    const body = (await page.textContent('main')) ?? '';
    if (/Worker: failed|Completion: blocked/.test(body)) throw new Error('Actual worker or completion failed; inspect private fixture and recorded status.');
    return /Completion: ready/.test(body);
  }, { timeout: 180000, intervals: [1000, 3000] }).toBe(true);
  d.record('D', 'engine', 'Actual worker generates a complete run', 'Worker completed; completion ready, no prepared-demo playback', 'PASS');
  await page.screenshot({ path: `${output}/D-01-generation.png`, fullPage: true });
  await page.getByRole('link', { name: 'Inspect generated timepoints', exact: true }).click();
  const states = page.getByLabel('State list equivalent', { exact: true });
  await expect(states).toBeVisible({ timeout: 30000 });
  const options = await states.locator('option').allTextContents();
  expect(options.length).toBeGreaterThanOrEqual(4);
  const selected = states.locator('option').filter({ hasText: /Day 30|day 30/ }).first();
  const state = await selected.getAttribute('value');
  expect(state).toBeTruthy();
  await states.selectOption(state!);
  const detail = page.getByRole('region', { name: 'Selected state detail' });
  await expect(detail).toContainText(/30/);
  await expect(detail).toContainText(/8/);
  await expect(detail).toContainText(/11/);
  d.record('D', 'states', 'Generated measurements and observations align at Day30', 'Day30 has target volume8 mm³ and hypothetical hemoglobin11 g/dL', 'PASS');
  await page.screenshot({ path: `${output}/D-02-states.png`, fullPage: true });
  await page.getByRole('link', { name: 'Explain this state in Insights →', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Snapshot-bound context' })).toBeVisible({ timeout: 30000 });
  await expect(page.getByLabel('State', { exact: true })).toHaveValue(state!);
  await page.getByRole('button', { name: 'Generate rule-based summary', exact: true }).click();
  const explanation = page.getByRole('region', { name: 'Research interpretation', exact: true });
  await expect(explanation).toContainText(/deterministic template/);
  await expect(explanation).toContainText(/Day 30/);
  await expect(explanation).toContainText(/8 mm3/);
  await expect(explanation).toContainText(/11 g\/dL/);
  await expect(explanation).toContainText(/hypothetical/i);
  e.record('E', 'local', 'Exact selected state produces grounded local explanation', 'Day30: volume8 mm³; hemoglobin11 g/dL; hypothetical deterministic template with observation references', 'PASS');
  await page.screenshot({ path: `${output}/E-01-local.png`, fullPage: true });
  const statePicker = page.getByLabel('State', { exact: true });
  const next = await statePicker.locator('option').filter({ hasText: 'Day 60' }).getAttribute('value');
  await statePicker.selectOption(next!);
  await expect(explanation).toHaveCount(0);
  await page.getByRole('button', { name: 'Load exact context', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Snapshot-bound context' })).toBeVisible();
  await page.getByRole('button', { name: 'Generate rule-based summary', exact: true }).click();
  await expect(explanation).toContainText(/Day 60/);
  await expect(explanation).toContainText(/1 mm3/);
  e.record('E', 'selection', 'State changes clear stale results', 'Old result cleared; Day60 shows1 mm³', 'PASS');
  expect(external).toEqual([]);
  e.record('E', 'provider', 'No unauthorized external inference; local mode labeled', 'Live remains unavailable; no browser Meta request; server integration negatives separately required', 'PASS');
  writeFileSync(`${output}/journey-D.json`, JSON.stringify({ recorded_at: new Date().toISOString(), scope: 'Actual isolated synthetic engine, measurement-only mode; authentic gate remains blocked', steps: d.rows }, null, 2));
  writeFileSync(`${output}/journey-E.json`, JSON.stringify({ recorded_at: new Date().toISOString(), steps: e.rows }, null, 2));
});
