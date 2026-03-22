import { describe, it, vi, beforeEach } from 'vitest';

describe('Skills API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should have skills API functions exported', async () => {
    const api = await import('@/api/skills');
    expect(api.getSkillsList).toBeDefined();
    expect(api.getSkillById).toBeDefined();
    expect(api.createSkill).toBeDefined();
    expect(api.updateSkill).toBeDefined();
    expect(api.deleteSkill).toBeDefined();
  });
});
