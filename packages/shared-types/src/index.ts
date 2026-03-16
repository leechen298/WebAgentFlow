export interface Recording {
  id: string;
  name: string;
  status: 'draft' | 'active' | 'archived';
  createdAt: string;
  updatedAt: string;
}

export interface Skill {
  id: string;
  name: string;
  version: string;
  description?: string;
  steps: unknown[];
  updatedAt: string;
}

export interface Run {
  id: string;
  skillId: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  startedAt?: string;
  finishedAt?: string;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
}
