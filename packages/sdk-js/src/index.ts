export interface ClientOptions {
  baseUrl?: string;
}

export interface WebAgentFlowClient {
  baseUrl: string;
}

export function createClient(options: ClientOptions = {}): WebAgentFlowClient {
  return {
    baseUrl: options.baseUrl ?? 'http://localhost:8001',
  };
}
