import { expect, test } from '@playwright/test';

test('COS-E2E-001 negative paths: invalid credentials fail safely', async ({ page }) => {
  test.setTimeout(180000);
  test.slow();
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(String(error).slice(0, 200)));
  const leaks: string[] = [];
  page.on('response', async (response) => {
    if (response.status() >= 500) {
      const body = await response.text().catch(() => '');
      if (/traceback|secret|password|api[_-]?key/i.test(body)) leaks.push(`${response.url()}: ${body.slice(0, 120)}`);
    }
  });

  await page.goto('http://127.0.0.1:3000/mesh-preview');
  await page.getByLabel('Project UUID', { exact: true }).fill('00000000-0000-0000-0000-000000000000');
  await page.getByLabel('Patient UUID', { exact: true }).fill('00000000-0000-0000-0000-000000000000');
  await page.getByLabel('Mesh QC report UUID', { exact: true }).fill('00000000-0000-0000-0000-000000000000');
  await page.getByLabel('Access token', { exact: true }).fill('invalid-token-probe');
  await page.getByRole('button', { name: 'Load private mesh', exact: true }).click();
  await expect(page.getByRole('status').first()).toContainText(/(Access denied|failed|invalid|unauthorized)/i, { timeout: 15000 });

  await page.goto('http://127.0.0.1:3000/cases?project=00000000-0000-0000-0000-000000000000');
  await page.waitForLoadState('domcontentloaded');
  await expect(page.getByText(/(restricted|not found|not visible|sign in|could not load)/i).first()).toBeVisible({ timeout: 15000 });

  expect(errors, `page errors: ${errors.join(' | ')}`).toEqual([]);
  expect(leaks, `server error leaks: ${leaks.join(' | ')}`).toEqual([]);
});
