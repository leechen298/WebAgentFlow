import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

// Get API base URL from environment variable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const USE_DEV_PROXY = import.meta.env.VITE_USE_DEV_PROXY === 'true';

// Determine the base URL to use
let BASE_URL: string;
if (USE_DEV_PROXY) {
  // Optional dev proxy mode - use /api prefix
  BASE_URL = '/api';
} else if (API_BASE_URL) {
  // Default mode - use explicit API base URL
  BASE_URL = API_BASE_URL;
} else {
  // No configuration - throw clear error
  throw new Error(
    'VITE_API_BASE_URL environment variable is required.\n' +
    'Please set it in your .env file, e.g.:\n' +
    'VITE_API_BASE_URL=http://192.168.31.109:8001'
  );
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
    // You can add auth tokens here later
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
