import { test, expect } from '@playwright/test';

test('has title', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/Quant LTTD/i);
});

test('shows loading or error or main dashboard', async ({ page }) => {
  await page.goto('http://localhost:5173/');
  
  // Either we see loading, error, or the dashboard title
  const hasText = await page.locator('text=LTTD Quant Dashboard').isVisible() ||
                  await page.locator('text=Loading interface...').isVisible() ||
                  await page.locator('text=Connection Error').isVisible();
                  
  expect(hasText).toBeTruthy();
});
