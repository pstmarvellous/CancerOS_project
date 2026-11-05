import { expect, test } from '@playwright/test';

test('truthful shell, keyboard control and narrow layout', async ({ page }) => {
  await page.goto(process.env.CANCEROS_BROWSER_BASE_URL ?? 'http://127.0.0.1:3000');
  await expect(page.getByRole('heading', {level:1})).toContainText('Explore Cancer');
  await expect(page.getByText(/not a diagnostic or treatment-recommendation tool/)).toBeVisible();
  const button=page.getByRole('link', {name:'Launch Digital Twin Demo'});
  await button.focus(); await expect(button).toBeFocused();
  await expect(button).toHaveAttribute('href', '/demo');
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
