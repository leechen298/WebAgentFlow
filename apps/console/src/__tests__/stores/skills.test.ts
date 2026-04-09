import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useSkillsStore } from '@/stores/skills';
import * as skillsApi from '@/api/skills';
import type { Skill } from '@web-agent-flow/shared-types';

// Mock the API
vi.mock('@/api/skills');

const mockSkill: Skill = {
  id: 'skill-123',
  name: 'Test Skill',
  description: 'Test description',
  version: '1.0.0',
  status: 'draft',
  recording_id: null,
  definition: {},
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('Skills Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should initialize with default state', () => {
    const store = useSkillsStore();
    expect(store.skills).toEqual([]);
    expect(store.currentSkill).toBeNull();
    expect(store.loading).toBe(false);
    expect(store.loadingList).toBe(false);
    expect(store.error).toBeNull();
    expect(store.hasSkills).toBe(false);
  });

  it('should fetch skills successfully', async () => {
    const store = useSkillsStore();
    const mockGetSkillsList = vi.mocked(skillsApi.getSkillsList);
    mockGetSkillsList.mockResolvedValue({ items: [mockSkill], has_next: false, next_cursor: null });

    await store.fetchSkills();

    expect(store.skills).toEqual([mockSkill]);
    expect(store.hasSkills).toBe(true);
  });

  it('should fetch a single skill', async () => {
    const store = useSkillsStore();
    const mockGetSkillById = vi.mocked(skillsApi.getSkillById);
    mockGetSkillById.mockResolvedValue(mockSkill);

    await store.fetchSkill('skill-123');

    expect(store.currentSkill).toEqual(mockSkill);
  });

  it('should create a skill and add to list', async () => {
    const store = useSkillsStore();
    const mockCreateSkill = vi.mocked(skillsApi.createSkill);
    const newSkill = { ...mockSkill, id: 'new-123' };
    mockCreateSkill.mockResolvedValue(newSkill);

    const result = await store.createSkill({
      name: 'New Skill',
      description: 'New description',
      version: '1.0.0',
      definition: {},
    });

    expect(result).toEqual(newSkill);
    expect(store.skills.length).toBe(1);
    expect(store.skills[0].id).toBe('new-123');
  });

  it('should update a skill', async () => {
    const store = useSkillsStore();
    const mockUpdateSkill = vi.mocked(skillsApi.updateSkill);
    const updated = { ...mockSkill, name: 'Updated' };
    mockUpdateSkill.mockResolvedValue(updated);

    store.skills = [mockSkill];

    const result = await store.updateSkill('skill-123', { name: 'Updated' });

    expect(result).toEqual(updated);
    expect(store.skills[0].name).toBe('Updated');
  });

  it('should delete a skill', async () => {
    const store = useSkillsStore();
    const mockDeleteSkill = vi.mocked(skillsApi.deleteSkill);
    mockDeleteSkill.mockResolvedValue({ skill_id: 'skill-123' });

    store.skills = [mockSkill];

    await store.deleteSkill('skill-123');

    expect(store.skills).toEqual([]);
  });

  it('should clear current skill', () => {
    const store = useSkillsStore();
    store.currentSkill = mockSkill;
    store.error = 'Some error';

    store.clearCurrent();

    expect(store.currentSkill).toBeNull();
    expect(store.error).toBeNull();
  });
});
