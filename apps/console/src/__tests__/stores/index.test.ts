import { describe, expect, it } from 'vitest';

describe('store index exports', () => {
  it('re-exports the app store composable', async () => {
    const stores = await import('@/stores');
    const app = await import('@/stores/app');

    expect(stores.useAppStore).toBe(app.useAppStore);
  });
});
