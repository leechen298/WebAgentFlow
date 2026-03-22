/**
 * API configuration for the extension
 */
export interface ApiConfig {
  baseURL: string;
  timeout: number;
}

/**
 * Get API configuration - default to localhost for development
 * Can be overridden by setting in extension storage
 */
const DEFAULT_API_BASE_URL = 'http://localhost:8001';
const API_TIMEOUT = 30000;
const CONFIG_STORAGE_KEY = 'webagentflow:api:config';

export async function getApiConfig(): Promise<ApiConfig> {
  try {
    const stored = await storage.getItem<ApiConfig>(CONFIG_STORAGE_KEY);
    if (stored && stored.baseURL) {
      return {
        baseURL: stored.baseURL,
        timeout: stored.timeout || API_TIMEOUT,
      };
    }
  } catch {
    // Ignore storage errors, use default
  }
  return {
    baseURL: DEFAULT_API_BASE_URL,
    timeout: API_TIMEOUT,
  };
}

export async function setApiConfig(config: Partial<ApiConfig>): Promise<void> {
  const current = await getApiConfig();
  const newConfig = { ...current, ...config };
  await storage.setItem(CONFIG_STORAGE_KEY, newConfig);
}
