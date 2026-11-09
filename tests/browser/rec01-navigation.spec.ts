import { expect, test, type Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const base = process.env.CANCEROS_BROWSER_BASE_URL ?? 'http://127.0.0.1:3001';
const output = process.env.CANCEROS_BROWSER_EVIDENCE_DIR ? `${process.env.CANCEROS_BROWSER_EVIDENCE_DIR}/navigation` : 'docs/engineering/testing/rec01-navigation';
const bundle = '.local/product-browser-fixture.json';
const caseCode = `REC01-${Date.now()}`;

function fixture() {
  const data = JSON.parse(readFileSync(bundle, 'utf8')) as {
    project_id: string; source_version_id: string; admin_token: string;
    viewer_token: string; outsider_token: string; synthetic_only: boolean;
  };
  expect(data.synthetic_only).toBe(true);
  return data;
}

async function signIn(page: Page, token: string, expectCreate = true) {
  await page.goto(`${base}/cases`);
  await page.getByLabel('Research access token').fill(token);
  await page.getByRole('button', { name: 'Sign in to research workspace' }).click();
  // Wait for genuinely authenticated UI (session cookie is set only after the
  // sign-in POST completes). Static signed-out text must not satisfy this.
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible({ timeout: 30000 });
  if (expectCreate) {
    await expect(page.getByRole('button', { name: 'New research case', exact: true })).toBeVisible({ timeout: 30000 });
  } else {
    await expect(page.getByRole('combobox')).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('button', { name: 'New research case', exact: true })).toBeHidden({ timeout: 30000 });
  }
}

test('REC-01 unified navigation: one case across twin, scenarios and clinical data with refresh, back, sign-out and isolation', async ({ page, context }) => {
  test.setTimeout(420000);
  page.setDefaultTimeout(30000);
  mkdirSync(output, { recursive: true });
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message.slice(0, 200)));
  page.on('console', (message) => {
    if (message.type() === 'error' && !/favicon|Failed to load resource|404|401/i.test(message.text())) errors.push(message.text().slice(0, 200));
  });
  const data = fixture();

  // 1. Sign in and create Research Demo Case A through the visible form.
  await signIn(page, data.admin_token);
  await page.getByRole('button', { name: 'New research case', exact: true }).click();
  const creation = page.getByRole('form', { name: 'Create research case' });
  await creation.getByLabel(/Case reference/).fill(caseCode);
  await creation.getByLabel(/Case title/).fill('Research Demo Case A');
  await creation.getByLabel(/Participant code/).fill(caseCode);
  await creation.getByLabel(/Source reference/).fill('Artificial register entry 042');
  await creation.getByRole('button', { name: 'Create Case', exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/detail\?/);
  const caseA = new URL(page.url());
  const project = caseA.searchParams.get('project')!;
  const patientA = caseA.searchParams.get('patient')!;
  expect(project).toBe(data.project_id);
  await expect(page.getByRole('heading', { name: 'Research Demo Case A', level: 3 })).toBeVisible({ timeout: 30000 });
  await page.screenshot({ path: `${output}/01-case-a-workspace.png` });

  // 2. Clinical Records tab works; then global Digital Twin keeps the case.
  await page.getByRole('tab', { name: /Clinical Records/ }).click();
  await expect(page.getByRole('region', { name: 'Clinical observation timeline' })).toBeVisible({ timeout: 30000 });
  await page.goto(`${base}/twin`);
  await expect(page.getByText('Restored your last opened case')).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('Open a case to inspect its lesion')).toBeHidden();
  await expect(page.getByText('This case has no 3D model yet. Add an imaging study to continue.')).toBeVisible();
  expect(page.url()).toContain(`patient=${patientA}`);
  await page.screenshot({ path: `${output}/02-twin-restored.png` });

  // 3. Global Scenarios keeps the case with no UUID entry.
  await page.goto(`${base}/simulation`);
  await expect(page).toHaveURL(new RegExp(`patient=${patientA}`), { timeout: 30000 });
  await expect(page.getByLabel('Project (one-time routing)')).toBeHidden();
  await expect(page.getByText(/Loading authorized branches for this case|authorized branch|No simulation branches exist/i).first()).toBeVisible({ timeout: 30000 });
  await page.screenshot({ path: `${output}/03-scenarios-restored.png` });

  // 4. Global Clinical Data (charts) keeps the case.
  await page.goto(`${base}/charts`);
  await expect(page.getByText('Restored your last opened case')).toBeVisible({ timeout: 30000 });
  expect(page.url()).toContain(`patient=${patientA}`);
  await page.screenshot({ path: `${output}/04-charts-restored.png` });

  // 5. Refresh preserves the authorized selection (URL now owns it; no restore banner needed).
  await page.reload();
  expect(page.url()).toContain(`patient=${patientA}`);
  await expect(page.getByText('Open a case to inspect its clinical charts')).toBeHidden();

  // 6. Browser-back preserves the selection.
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`patient=${patientA}`), { timeout: 30000 });
  await expect(page.getByLabel('Project (one-time routing)')).toBeHidden();
  await expect(page.getByText(/Loading authorized branches for this case|authorized branch|No simulation branches exist/i).first()).toBeVisible({ timeout: 30000 });

  // 7. Cross-case isolation: create Case B, switch, assert A content absent.
  await page.goto(`${base}/cases?project=${project}`);
  await page.getByRole('button', { name: 'New research case', exact: true }).click();
  const codeB = `${caseCode}-B`;
  const creationB = page.getByRole('form', { name: 'Create research case' });
  await creationB.getByLabel(/Case reference/).fill(codeB);
  await creationB.getByLabel(/Case title/).fill('Research Demo Case B');
  await creationB.getByLabel(/Participant code/).fill(codeB);
  await creationB.getByLabel(/Source reference/).fill('Artificial register entry 043');
  await creationB.getByRole('button', { name: 'Create Case', exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/detail\?/);
  const patientB = new URL(page.url()).searchParams.get('patient')!;
  expect(patientB).not.toBe(patientA);
  await expect(page.getByRole('heading', { name: 'Research Demo Case B', level: 3 })).toBeVisible({ timeout: 30000 });
  await page.goto(`${base}/twin`);
  await expect(page).toHaveURL(new RegExp(`patient=${patientB}`), { timeout: 30000 });
  expect(page.url()).not.toContain(`patient=${patientA}`);
  await page.screenshot({ path: `${output}/05-case-b-isolation.png` });

  // Query-only navigation uses the same history mechanism as state pickers.
  // It must refetch B instead of leaving A mounted behind a changed URL.
  await page.goto(`${base}/charts?project=${project}&patient=${patientA}`);
  await expect(page.getByText(new RegExp(`Case: ${patientA.slice(0, 8)}`))).toBeVisible();
  const rebound = page.waitForResponse(response => response.url().includes('/api/clinical-charts?') && response.url().includes(`patient=${patientB}`));
  await page.evaluate(url => window.history.pushState(null, '', url), `/charts?project=${project}&patient=${patientB}`);
  expect((await rebound).status()).toBe(200);
  await expect(page.getByText(new RegExp(`Case: ${patientB.slice(0, 8)}`))).toBeVisible();
  await expect(page.getByText(new RegExp(`Case: ${patientA.slice(0, 8)}`))).toBeHidden();
  await page.goBack();
  await expect(page.getByText(new RegExp(`Case: ${patientA.slice(0, 8)}`))).toBeVisible();

  // 8. Stale state selection fails gracefully without content.
  await page.goto(`${base}/insights?project=${project}&patient=${patientB}&state=00000000-0000-4000-8000-000000000099`);
  await expect(page.getByText(/unavailable in this authorized case|Missing state selection|Open a case first/i).first()).toBeVisible({ timeout: 60000 });
  await page.screenshot({ path: `${output}/06-stale-state.png` });

  // 9. Sign out removes access to protected case content.
  await page.goto(`${base}/cases`);
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByText('Research access token')).toBeVisible({ timeout: 30000 });
  await page.goto(`${base}/cases/detail?project=${project}&patient=${patientA}`);
  await expect(page.getByText(/Sign in with an authorized session|not available to your account|Open a case first/i).first()).toBeVisible({ timeout: 30000 });
  const cookies = await context.cookies();
  expect(cookies.find((cookie) => cookie.name === 'canceros-research-session')).toBeUndefined();
  const stored = await page.evaluate(() => localStorage.getItem('canceros:last_case'));
  expect(stored).toBeNull();
  await page.screenshot({ path: `${output}/07-signed-out.png` });

  // 10. Inaccessible case: a viewer (no editor rights) is denied with no content.
  const viewer = await context.newPage();
  await signIn(viewer, data.viewer_token, false);
  await viewer.goto(`${base}/cases/detail?project=${project}&patient=${patientA}`);
  await expect(viewer.getByText(/cannot perform this action|not available to your account|restricted for your role/i).first()).toBeVisible({ timeout: 30000 });
  const viewerBody = (await viewer.textContent('main')) ?? '';
  expect(viewerBody).not.toContain('Research Demo Case A');
  await viewer.screenshot({ path: `${output}/08-viewer-denied.png` });
  await viewer.close();

  expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
  writeFileSync(`${output}/rec01-navigation-evidence.json`, JSON.stringify({
    recorded_at: new Date().toISOString(),
    scope: 'Real RS256/SQL/private-storage services; artificial sources and observations only',
    case_a: patientA, case_b: patientB, project,
    journey: ['case-a-created', 'clinical-records', 'twin-restored', 'scenarios-restored', 'charts-restored', 'refresh-preserved', 'back-preserved', 'case-b-isolation', 'stale-state-graceful', 'sign-out-clears-access', 'viewer-denied'],
    browser_errors: errors,
  }, null, 2));
});
