import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

// Default API base URL - can be overridden via env
const DEFAULT_BASE_URL = 'http://localhost:8000';
const BASE_URL = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL;

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
