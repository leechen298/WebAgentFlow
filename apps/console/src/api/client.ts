import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

// Get API base URL from environment variable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const USE_DEV_PROXY = import.meta.env.VITE_USE_DEV_PROXY === 'true';

// Resolve API configuration with clear determination
export interface ApiConfig {
  mode: 'direct' | 'proxy';
  baseURL: string;
  useDevProxy: boolean;
  configuredApiBaseUrl?: string;
}

export function resolveApiConfig(): ApiConfig {
  if (USE_DEV_PROXY) {
    return {
      mode: 'proxy',
      baseURL: '/api',
      useDevProxy: true,
      configuredApiBaseUrl: API_BASE_URL,
    };
  } else if (API_BASE_URL) {
    return {
      mode: 'direct',
      baseURL: API_BASE_URL,
      useDevProxy: false,
      configuredApiBaseUrl: API_BASE_URL,
    };
  } else {
    throw new Error(
      'VITE_API_BASE_URL environment variable is required.\n' +
      'Please set it in your .env file, e.g.:\n' +
      'VITE_API_BASE_URL=http://192.168.31.109:8001'
    );
  }
}

const apiConfig = resolveApiConfig();
const BASE_URL = apiConfig.baseURL;

// Log API configuration in development for debugging
if (import.meta.env.DEV) {
  // eslint-disable-next-line no-console
  console.log(
    `%c[API Config] mode=${apiConfig.mode}, baseURL=%c${apiConfig.baseURL}`,
    'color: #1890ff; font-weight: bold;',
    'color: #52c41a; font-weight: bold;'
  );
  if (apiConfig.mode === 'proxy' && apiConfig.configuredApiBaseUrl) {
    // eslint-disable-next-line no-console
    console.log(
      `%c[API Config] Note: VITE_API_BASE_URL=${apiConfig.configuredApiBaseUrl} is ignored when VITE_USE_DEV_PROXY=true`,
      'color: #faad14; font-weight: bold;'
    );
  }
}

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    config.headers['X-Locale'] = localStorage.getItem('locale') || navigator.language;
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle envelope unpacking
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const data = response.data as { code: number; msg: string; data: unknown };
    if (data.code !== 0) {
      // Business error
      const error = new Error(data.msg || 'Request failed');
      (error as unknown as Record<string, unknown>).code = data.code;
      return Promise.reject(error);
    }
    // Return just the data part - cast to unknown for the interceptor
    return data.data as unknown as AxiosResponse;
  },
  (error: AxiosError) => {
    // Handle HTTP errors
    let message = 'Network error';
    if (error.response) {
      const status = error.response.status;
      if (status === 400) {
        message = 'Bad request';
      } else if (status === 404) {
        message = 'Resource not found';
      } else if (status === 500) {
        message = 'Server error';
      } else {
        message = `HTTP error: ${status}`;
      }
      // Try to extract message from error response
      const errorData = error.response.data as { msg?: string };
      if (errorData && errorData.msg) {
        message = errorData.msg;
      }
    } else if (error.request) {
      message = 'No response from server';
    }
    const apiError = new Error(message);
    (apiError as unknown as Record<string, unknown>).original = error;
    return Promise.reject(apiError);
  }
);

export default apiClient;
