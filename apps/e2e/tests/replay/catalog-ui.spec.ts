import { expect, test, type Page } from '@playwright/test';

import { consoleUrl, validationUrl } from '../../fixtures/config';
import { loadReplayFixtures, type ReplayFixtureFile } from '../../fixtures/learnedPaths';

let seeded: ReplayFixtureFile;

test.beforeAll(async () => {
  seeded = await loadReplayFixtures();
});

function collectForbiddenAutonomousRequests(page: Page): string[] {
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

  return forbiddenRequests;
}

async function openCatalog(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en');
  });

  await page.goto(consoleUrl('/exploration/learned-paths'));
  await expect(page.locator('.learned-path-catalog .catalog-title')).toHaveText('LearnedPath');
}

function scenarioRow(page: Page, scenario: string) {
  return page.locator('tr').filter({ hasText: scenario }).first();
}

async function selectTrustFilter(page: Page, trust: string): Promise<void> {
  await page.locator('.learned-path-catalog .ant-select-selector').first().click();
  await page.locator('.ant-select-item-option').filter({ hasText: new RegExp(trust, 'i') }).first().click();
}

test('LearnedPath catalog lists seeded paths with trust labels', async ({ page }) => {
  const forbiddenRequests = collectForbiddenAutonomousRequests(page);
  await openCatalog(page);

  const happyRow = scenarioRow(page, seeded.fixtures.happy.scenario);
  await expect(happyRow).toBeVisible();
  await expect(happyRow).toContainText(/confirmed/i);

  const flakyRow = scenarioRow(page, seeded.fixtures.flaky.scenario);
  await expect(flakyRow).toBeVisible();
  await expect(flakyRow).toContainText(/flaky/i);

  const deprecatedRow = scenarioRow(page, seeded.fixtures.deprecated.scenario);
  await expect(deprecatedRow).toBeVisible();
  await expect(deprecatedRow).toContainText(/deprecated/i);

  expect(forbiddenRequests).toEqual([]);
});

test('LearnedPath catalog filters by trust', async ({ page }) => {
  const forbiddenRequests = collectForbiddenAutonomousRequests(page);
  await openCatalog(page);

  await selectTrustFilter(page, 'Flaky');

  const flakyRow = scenarioRow(page, seeded.fixtures.flaky.scenario);
  await expect(flakyRow).toBeVisible();
  await expect(flakyRow).toContainText(/flaky/i);
  await expect(scenarioRow(page, seeded.fixtures.happy.scenario)).toHaveCount(0);
  await expect(scenarioRow(page, seeded.fixtures.deprecated.scenario)).toHaveCount(0);

  expect(forbiddenRequests).toEqual([]);
});

test('LearnedPath catalog drawer exposes replay and actions sections', async ({ page }) => {
  const forbiddenRequests = collectForbiddenAutonomousRequests(page);
  await openCatalog(page);

  const scenario = seeded.fixtures.happy.scenario;
  const row = scenarioRow(page, scenario);
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: 'View actions' }).click();

  const drawer = page.locator('.ant-drawer').filter({ hasText: scenario });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByText('Replay this path')).toBeVisible();
  await expect(drawer.getByPlaceholder('Target URL')).toBeVisible();
  await expect(drawer.getByRole('button', { name: 'Replay' })).toBeDisabled();
  await expect(drawer.getByRole('heading', { name: 'Actions' })).toBeVisible();
  await expect(drawer.getByText('Step 1')).toBeVisible();
  await expect(drawer.locator('.action-json').first()).toContainText('#search-name');

  expect(forbiddenRequests).toEqual([]);
});

test('LearnedPath catalog can replay a seeded happy path', async ({ page }) => {
  const forbiddenRequests = collectForbiddenAutonomousRequests(page);
  await openCatalog(page);

  const scenario = seeded.fixtures.happy.scenario;
  const row = scenarioRow(page, scenario);
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
