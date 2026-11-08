import { expect, test } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const base = 'http://127.0.0.1:3001';
const output = 'docs/engineering/testing/rec05-cases';
const bundle = '.local/product-browser-fixture.json';

function data() {
  const parsed = JSON.parse(readFileSync(bundle, 'utf8')) as {
    project_id: string; source_version_id: string; admin_token: string; viewer_token: string; synthetic_only: boolean;
  };
  expect(parsed.synthetic_only).toBe(true);
  return parsed;
}

test('REC-05 research cases: create, profile, observe, correct, refresh, isolation, sign-out', async ({ page, context }) => {
  test.setTimeout(420000);
  page.setViewportSize({ width: 1440, height: 1000 });
  mkdirSync(output, { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message.slice(0, 200)));
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|Failed to load resource/i.test(message.text())) errors.push(message.text().slice(0, 200));
  });
  const fixture = data();
  const codeA = `REC05-${Date.now()}`;

  // Sign in as admin; primary action is New research case.
  await page.goto(`${base}/cases`);
  await page.getByLabel('Research access token').fill(fixture.admin_token);
  await page.getByRole('button', { name: 'Sign in to research workspace' }).click();
  await expect(page.getByRole('button', { name: 'New research case', exact: true })).toBeVisible({ timeout: 30000 });

  // 1. Create Case A with plain-language fields.
  await page.getByRole('button', { name: 'New research case', exact: true }).click();
  const creation = page.getByRole('form', { name: 'Create research case' });
  await creation.getByLabel(/Case title/).fill('Breast Cancer Research Example A');
  await creation.getByLabel(/Case reference/).fill(codeA);
  await creation.getByLabel(/Participant code/).fill(codeA);
  await creation.getByLabel(/Source reference/).fill('Artificial register entry 042');
  await expect(creation.getByText(/Artificial demonstration/i).first()).toBeVisible();
  await creation.getByRole('button', { name: 'Create Case', exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/detail\?/);
  const urlA = new URL(page.url());
  const patientA = urlA.searchParams.get('patient')!;
  await expect(page.getByRole('heading', { name: 'Breast Cancer Research Example A', level: 3 })).toBeVisible({ timeout: 30000 });
  await page.screenshot({ path: `${output}/01-case-a-created.png` });

  // 2-3. Save the profile and observe it.
  await expect(page.getByText(codeA, { exact: true }).first()).toBeVisible({ timeout: 30000 });
  const profile = page.getByRole('region', { name: 'Research profile editor' });
  await expect(profile.getByText('Artificial register entry 042')).toBeVisible();
  await page.screenshot({ path: `${output}/02-profile.png` });

  // Save an artificial observation: Hemoglobin 12.3 g/dL.
  await page.getByRole('tab', { name: /Clinical Records/ }).click();
  const timeline = page.getByRole('region', { name: 'Clinical observation timeline' });
  await expect(timeline.getByText(/No clinical observations|observations/i).first()).toBeVisible({ timeout: 30000 });
  const form = page.getByRole('form', { name: 'Save clinical observation' });
  await expect(page.getByText(/Artificial demonstration record/)).toBeVisible();
  await form.getByRole('button', { name: /Laboratory/i }).click().catch(() => {});
  await form.getByLabel('Specific concept').selectOption('hemoglobin');
  await form.getByLabel(/Source original term/).fill('Artificial hemoglobin observation');
  await form.getByLabel(/Source reference/).fill('Artificial report row 1');
  await form.getByLabel(/Collection date|Timestamp with TZ/).fill('2026-11-01');
  await form.getByLabel(/Measured value|Value/).fill('12.3');
  await form.getByRole('button', { name: 'Save observation', exact: true }).click();
  await expect(timeline.getByText('12.3 g/dL', { exact: true })).toBeVisible({ timeout: 30000 });
  await page.screenshot({ path: `${output}/03-observation.png` });

  // 4. Correct to 12.4; previous revision retained.
  const originalRow = timeline.getByRole('row').filter({ hasText: 'Artificial hemoglobin observation' });
  await originalRow.getByRole('button', { name: 'Correct' }).click();
  await form.getByLabel(/Source original term/).fill('Artificial corrected hemoglobin observation');
  await form.getByLabel(/Measured value|Value/).fill('12.4');
  await form.getByRole('button', { name: 'Save observation', exact: true }).click();
  await expect(timeline.getByText('12.4 g/dL', { exact: true })).toBeVisible({ timeout: 30000 });
  await expect(originalRow.getByText(/Superseded/)).toBeVisible();
  await page.screenshot({ path: `${output}/04-correction.png` });

  // 5. Refresh retains the latest value and history.
  await page.reload();
  await page.getByRole('tab', { name: /Clinical Records/ }).click();
  await expect(page.getByRole('region', { name: 'Clinical observation timeline' }).getByText('12.4 g/dL', { exact: true })).toBeVisible({ timeout: 30000 });
  await expect(page.getByRole('region', { name: 'Clinical observation timeline' }).getByText(/Superseded/).first()).toBeVisible({ timeout: 30000 });

  // 6-7. Create Case B; verify B cannot see A's protected information.
  await page.goto(`${base}/cases?project=${fixture.project_id}`);
  await page.getByRole('button', { name: 'New research case', exact: true }).click();
  const codeB = `${codeA}-B`;
  const creationB = page.getByRole('form', { name: 'Create research case' });
  await creationB.getByLabel(/Case title/).fill('Breast Cancer Research Example B');
  await creationB.getByLabel(/Case reference/).fill(codeB);
  await creationB.getByLabel(/Participant code/).fill(codeB);
  await creationB.getByLabel(/Source reference/).fill('Artificial register entry 043');
  await creationB.getByRole('button', { name: 'Create Case', exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/detail\?/);
  const patientB = new URL(page.url()).searchParams.get('patient')!;
  expect(patientB).not.toBe(patientA);
  await page.goto(`${base}/cases/detail?project=${fixture.project_id}&patient=${patientB}`);
  const bodyB = ((await page.textContent('main')) ?? '');
  expect(bodyB).not.toContain('12.4 g/dL');
  expect(bodyB).not.toContain(codeA);
  await page.screenshot({ path: `${output}/05-case-b-isolation.png` });

  // 8. Sign out revokes access.
  await page.goto(`${base}/cases`);
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByText('Research access token')).toBeVisible({ timeout: 30000 });
  const stored = await page.evaluate(() => localStorage.getItem('canceros:last_case'));
  expect(stored).toBeNull();
  await page.goto(`${base}/cases/detail?project=${fixture.project_id}&patient=${patientA}`);
  await expect(page.getByText(/Sign in with an authorized session|not available to your account/i).first()).toBeVisible({ timeout: 30000 });
  const cookies = await context.cookies();
  expect(cookies.find((cookie) => cookie.name === 'canceros-research-session')).toBeUndefined();
  const signedOutBody = ((await page.textContent('main')) ?? '');
  expect(signedOutBody).not.toContain('12.4 g/dL');
  await page.screenshot({ path: `${output}/06-signed-out.png` });

  expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
  writeFileSync(`${output}/rec05-cases-evidence.json`, JSON.stringify({
    recorded_at: new Date().toISOString(),
    scope: 'Real RS256/SQL/private-storage services; artificial sources and observations only',
    case_a: patientA, case_b: patientB, project: fixture.project_id,
    journey: ['create-a', 'profile', 'observe', 'correct', 'refresh', 'case-b-isolation', 'sign-out'],
    browser_errors: errors,
  }, null, 2));
});
