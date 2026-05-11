import { expect, test } from '@playwright/test';

import { validationUrl } from '../../fixtures/config';

const noMatchName = 'zzzz-no-match-9999';

test.describe('Validation-site browser smoke', () => {
  test('login page renders key controls', async ({ page }) => {
    await page.goto(validationUrl('/login'));

    await expect(page).toHaveTitle(/Sign in|登录|ログイン/);
    await expect(page.locator('#username')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await expect(page.getByRole('alert')).toHaveCount(0);
  });

  test('login invalid credentials shows error', async ({ page }) => {
    await page.goto(validationUrl('/login'));

    await page.locator('#username').fill('wrong');
    await page.locator('#password').fill('wrong');
    await page.locator('button[type="submit"]').click();

    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page.getByRole('alert')).toContainText(
      /用户名或密码错误|Invalid username or password|ユーザー名またはパスワードが無効です/,
    );
    await expect(page).toHaveURL(/\/login$/);
  });

  test('users page renders search controls and seeded results', async ({ page }) => {
    await page.goto(validationUrl('/users'));

    await expect(page.locator('#search-name')).toBeVisible();
    await expect(page.locator('#search-status')).toBeVisible();
    await expect(page.locator('#btn-search')).toBeVisible();
    await expect(page.locator('.result-card')).toBeVisible();
    await expect(page.locator('.user-table')).toBeVisible();
    await expect(page.getByText('alice@example.com')).toBeVisible();
  });

  test('users search by name filters results', async ({ page }) => {
    await page.goto(validationUrl('/users'));

    await page.locator('#search-name').fill('alice');
    await page.locator('#btn-search').click();

    await expect(page).toHaveURL(/\/users\?name=alice$/);
    await expect(page.getByText('alice@example.com')).toBeVisible();
    await expect(page.locator('.result-meta')).toContainText(/1 user|1 位用户|1 人/);
  });

  test('users no-match search shows empty state', async ({ page }) => {
    await page.goto(validationUrl('/users'));

    await page.locator('#search-name').fill(noMatchName);
    await page.locator('#btn-search').click();

    await expect(page).toHaveURL(new RegExp(`/users\\?name=${noMatchName}$`));
    await expect(page.locator('.user-table')).toContainText(
      /No users found|未找到匹配的用户|該当するユーザーはいません/,
    );
  });
});
