import { defineStore } from 'pinia';
import type { Recording, Run, Skill } from '@web-agent-flow/shared-types';

const now = new Date().toISOString();

export const useAppStore = defineStore('app', {
  state: () => ({
    recordings: [
      {
        id: 'rec-001',
        name: 'Placeholder recording',
        status: 'draft',
        createdAt: now,
        updatedAt: now,
      },
    ] as Recording[],
    skills: [
      {
        id: 'skill-001',
        name: 'Placeholder skill',
        version: '0.1.0',
        description: 'Initial schema placeholder',
        steps: [],
        updatedAt: now,
      },
    ] as Skill[],
    runs: [
      {
        id: 'run-001',
        skillId: 'skill-001',
        status: 'queued',
        startedAt: now,
      },
    ] as Run[],
  }),
});
