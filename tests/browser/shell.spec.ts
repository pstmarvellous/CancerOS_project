import { expect, test } from '@playwright/test';

test('truthful shell, keyboard control and narrow layout', async ({ page }) => {
  await page.goto('http://127.0.0.1:3000');
  await expect(page.getByRole('heading', {level:1})).toHaveText('A foundation for traceable research.');
  await expect(page.getByText('Research prototype. Not validated for diagnosis or treatment decisions.', {exact:true})).toBeVisible();
  const button=page.getByRole('button', {name:'Check API connection'});
  await button.focus(); await expect(button).toBeFocused();
  await button.press('Enter');
  await expect(page.getByRole('status')).toHaveText(/API process (reachable|unavailable)/);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
