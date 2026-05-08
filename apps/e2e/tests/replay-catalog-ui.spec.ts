import { expect, test } from '@playwright/test';

import { consoleUrl, validationUrl } from '../fixtures/config';
import { loadReplayFixtures, type ReplayFixtureFile } from '../fixtures/learnedPaths';

let seeded: ReplayFixtureFile;

test.beforeAll(async () => {
  seeded = await loadReplayFixtures();
});

test('LearnedPath catalog can replay a seeded happy path', async ({ page }) => {
  const forbiddenRequests: string[] = [];
  page.on('request', (request) => {
    const url = request.url();
    if (
      url.includes('/exploration/autonomous-runs') ||
      url.includes('/exploration/autonomous-runs/stream')
    ) {
      forbiddenRequests.push(url);
    }
  });

  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en');
  });

  await page.goto(consoleUrl('/exploration/learned-paths'));

  const scenario = seeded.fixtures.happy.scenario;
  const row = page.locator('tr').filter({ hasText: scenario }).first();
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: 'View actions' }).click();

  await expect(page.getByText('Replay this path')).toBeVisible();
  await page.getByPlaceholder('Target URL').fill(validationUrl('/users'));
  await page.getByRole('button', { name: 'Replay' }).click();

  await expect(page.getByText('Succeeded')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText('No drift')).toBeVisible();
  await expect(page.getByText(validationUrl('/users'), { exact: false })).toBeVisible();
  await expect(page.getByText('Step 0')).toBeVisible();
  expect(forbiddenRequests).toEqual([]);
});
