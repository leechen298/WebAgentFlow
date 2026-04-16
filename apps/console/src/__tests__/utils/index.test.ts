import { describe, expect, it } from 'vitest';

describe('utils index exports', () => {
  it('re-exports json helpers', async () => {
    const utils = await import('@/utils');
    const json = await import('@/utils/json');

    expect(utils.safeParseJson).toBe(json.safeParseJson);
    expect(utils.formatJsonString).toBe(json.formatJsonString);
  });
});
