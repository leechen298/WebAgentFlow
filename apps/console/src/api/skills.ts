import apiClient from './client';
import type { Skill, SkillCreate, SkillUpdate, DeleteResponse, CursorPage } from '@web-agent-flow/shared-types';

export async function getSkillsList(params?: { limit?: number; cursor?: string }): Promise<CursorPage<Skill>> {
  return await apiClient.get('/skills/list', { params }) as unknown as CursorPage<Skill>;
}

export async function getSkillById(skillId: string): Promise<Skill> {
  return await apiClient.get('/skills/get', {
    params: { skill_id: skillId }
  }) as unknown as Skill;
}

export async function createSkill(payload: SkillCreate): Promise<Skill> {
  return await apiClient.post('/skills/create', payload) as unknown as Skill;
}

export async function updateSkill(skillId: string, updateData: SkillUpdate): Promise<Skill> {
  return await apiClient.post('/skills/update', {
    skill_id: skillId,
    update_data: updateData
  }) as unknown as Skill;
}

export async function deleteSkill(skillId: string): Promise<DeleteResponse> {
  return await apiClient.post('/skills/delete', {
    skill_id: skillId
  }) as unknown as DeleteResponse;
}
