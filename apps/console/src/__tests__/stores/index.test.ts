import { describe, expect, it } from 'vitest';

describe('store index exports', () => {
  it('re-exports store composables', async () => {
    const stores = await import('@/stores');
    const app = await import('@/stores/app');
    const recordings = await import('@/stores/recordings');
    const skills = await import('@/stores/skills');
    const runs = await import('@/stores/runs');

    expect(stores.useAppStore).toBe(app.useAppStore);
    expect(stores.useRecordingsStore).toBe(recordings.useRecordingsStore);
    expect(stores.useSkillsStore).toBe(skills.useSkillsStore);
    expect(stores.useRunsStore).toBe(runs.useRunsStore);
  });
});
