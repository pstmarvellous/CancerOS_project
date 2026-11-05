import { expect, test } from '@playwright/test';

const routes = [
  '/',
  '/cases',
  '/twin',
  '/states',
  '/charts',
  '/simulation',
  '/insights',
  '/timeline',
  '/evaluation',
  '/guided-demo',
  '/mesh-preview',
];

test('COS-E2E-001 journey probe: all routes render without console errors', async ({ page }) => {
  test.setTimeout(180000);
  test.slow();
  const errors: string[] = [];
  const failed: string[] = [];
  const fs = await import('node:fs');
  fs.mkdirSync('docs/engineering/testing/browser-e2e', { recursive: true });
  const summary: Array<{ route: string; title: string; status: string }> = [];
  for (const route of routes) {
    const routeErrors: string[] = [];
    const onPageError = (error: Error) => routeErrors.push(String(error).slice(0, 200));
    const onConsole = (message: { type: () => string; text: () => string }) => {
      if (message.type() === 'error' && !message.text().includes('404')) routeErrors.push(message.text().slice(0, 200));
    };
    const onResponse = (response: { status: () => number; url: () => string }) => {
      if (response.status() >= 500) failed.push(`${response.status()} ${response.url()}`);
    };
    page.on('pageerror', onPageError);
    page.on('console', onConsole);
    page.on('response', onResponse);
    await page.goto(`http://127.0.0.1:3000${route}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(800);
    const heading = page.getByRole('heading', { level: 1 });
    const title = (await heading.count()) ? ((await heading.first().textContent()) ?? '').slice(0, 120) : '(no h1)';
    expect(title, `route ${route} must not render the 404 page`).not.toMatch(/^404/);
    const needsSelection = await page.getByText('Open an authorized case', { exact: false }).count();
    summary.push({ route, title, status: needsSelection ? 'gated-empty-state' : 'rendered' });
    for (const error of routeErrors) errors.push(`${route} :: ${error}`);
    await page.screenshot({ path: `docs/engineering/testing/browser-e2e/route-${route === '/' ? 'home' : route.slice(1)}.png` });
    page.off('pageerror', onPageError);
    page.off('console', onConsole);
    page.off('response', onResponse);
  }
  fs.writeFileSync(
    'docs/engineering/testing/browser-e2e/route-summary.json',
    JSON.stringify({ recorded_at: new Date().toISOString(), summary, consoleErrors: errors, failedResponses: failed }, null, 2),
  );
  expect(failed, `HTTP 5xx responses: ${failed.join('; ')}`).toEqual([]);
  expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
  const gated = summary.filter((entry) => entry.status === 'gated-empty-state').map((entry) => entry.route);
  expect(gated.length, `expected only case-gated empty states, got: ${JSON.stringify(summary)}`).toBeGreaterThan(0);
  for (const route of ['/twin', '/states', '/charts', '/insights']) {
    expect(gated, `route ${route} should gate on case selection`).toContain(route);
  }
});
