import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  createRecording,
  deleteRecording,
  getRecordingById,
  getRecordingsList,
  getRecordingSteps,
  getAgentSteps,
  getNormalizedRecording,
  updateRecording,
} from '@/api/recordings';
import { createRun, deleteRun, getRunById, getRunsList, updateRun } from '@/api/runs';
import { createSkill, deleteSkill, getSkillById, getSkillsList, updateSkill } from '@/api/skills';

const { get, post } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: { get, post },
}));

describe('resource API wrappers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('covers recordings endpoints', async () => {
    get.mockResolvedValueOnce({ items: [] });
    await getRecordingsList({ limit: 5, cursor: 'abc' });
    expect(get).toHaveBeenCalledWith('/recordings/list', { params: { limit: 5, cursor: 'abc' } });

    get.mockResolvedValueOnce({ id: 'rec-1' });
    await getRecordingById('rec-1');
    expect(get).toHaveBeenCalledWith('/recordings/get', { params: { recording_id: 'rec-1' } });

    post.mockResolvedValueOnce({ id: 'rec-1' });
    await createRecording({ name: 'x', status: 'draft', source: 'ui', events: [], meta: null } as never);
    expect(post).toHaveBeenCalledWith('/recordings/create', expect.objectContaining({ name: 'x' }));

    post.mockResolvedValueOnce({ id: 'rec-1' });
    await updateRecording('rec-1', { name: 'y' });
    expect(post).toHaveBeenCalledWith('/recordings/update', { recording_id: 'rec-1', update_data: { name: 'y' } });

    post.mockResolvedValueOnce({ success: true });
    await deleteRecording('rec-1');
    expect(post).toHaveBeenCalledWith('/recordings/delete', { recording_id: 'rec-1' });

    get.mockResolvedValueOnce({});
    await getNormalizedRecording('rec-1');
    expect(get).toHaveBeenCalledWith('/recordings/get_normalized', { params: { recording_id: 'rec-1' } });

    get.mockResolvedValueOnce({});
    await getRecordingSteps('rec-1');
    expect(get).toHaveBeenCalledWith('/recordings/get_steps', { params: { recording_id: 'rec-1' } });

    get.mockResolvedValueOnce({});
    await getAgentSteps('rec-1');
    expect(get).toHaveBeenCalledWith('/recordings/get_agent_steps', { params: { recording_id: 'rec-1' } });
  });

  it('covers runs endpoints', async () => {
    get.mockResolvedValueOnce({ items: [] });
    await getRunsList({ limit: 5 });
    expect(get).toHaveBeenCalledWith('/runs/list', { params: { limit: 5 } });

    get.mockResolvedValueOnce({ id: 'run-1' });
    await getRunById('run-1');
    expect(get).toHaveBeenCalledWith('/runs/get', { params: { run_id: 'run-1' } });

    post.mockResolvedValueOnce({ id: 'run-1' });
    await createRun({ skill_id: 'skill-1', status: 'pending' } as never);
    expect(post).toHaveBeenCalledWith('/runs/create', expect.objectContaining({ skill_id: 'skill-1' }));

    post.mockResolvedValueOnce({ id: 'run-1' });
    await updateRun('run-1', { status: 'running' });
    expect(post).toHaveBeenCalledWith('/runs/update', { run_id: 'run-1', update_data: { status: 'running' } });

    post.mockResolvedValueOnce({ success: true });
    await deleteRun('run-1');
    expect(post).toHaveBeenCalledWith('/runs/delete', { run_id: 'run-1' });
  });

  it('covers skills endpoints', async () => {
    get.mockResolvedValueOnce({ items: [] });
    await getSkillsList({ limit: 5 });
    expect(get).toHaveBeenCalledWith('/skills/list', { params: { limit: 5 } });

    get.mockResolvedValueOnce({ id: 'skill-1' });
    await getSkillById('skill-1');
    expect(get).toHaveBeenCalledWith('/skills/get', { params: { skill_id: 'skill-1' } });

    post.mockResolvedValueOnce({ id: 'skill-1' });
    await createSkill({ name: 'Skill', version: '1.0.0', status: 'draft', definition: {} } as never);
    expect(post).toHaveBeenCalledWith('/skills/create', expect.objectContaining({ name: 'Skill' }));

    post.mockResolvedValueOnce({ id: 'skill-1' });
    await updateSkill('skill-1', { status: 'published' });
    expect(post).toHaveBeenCalledWith('/skills/update', { skill_id: 'skill-1', update_data: { status: 'published' } });

    post.mockResolvedValueOnce({ success: true });
    await deleteSkill('skill-1');
    expect(post).toHaveBeenCalledWith('/skills/delete', { skill_id: 'skill-1' });
  });
});
