import apiClient from './client';

export interface HealthStatus {
  status: string;
  database?: string;
}

export async function getHealth(): Promise<HealthStatus> {
  return await apiClient.get('/health') as unknown as HealthStatus;
}
