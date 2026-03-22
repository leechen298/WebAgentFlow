import axios, { AxiosError, AxiosInstance } from 'axios';
import { getApiConfig } from './config';
import type { ApiResponse, ApiErrorResponse } from '@web-agent-flow/shared-types';

/**
 * Create an axios instance with the current API configuration
 */
export async function createApiClient(): Promise<AxiosInstance> {
  const config = await getApiConfig();

  const client = axios.create({
    baseURL: config.baseURL,
    timeout: config.timeout,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Response interceptor - handle envelope unpacking
  client.interceptors.response.use(
    (response) => {
      const data = response.data as ApiResponse<unknown>;
      if (data.code !== 0) {
        // Business error
        const error = new Error(data.msg || 'Request failed');
        (error as unknown as Record<string, unknown>).code = data.code;
        return Promise.reject(error);
      }
      return data.data;
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
        const errorData = error.response.data as ApiErrorResponse;
        if (errorData && errorData.msg) {
          message = errorData.msg;
        }
      } else if (error.request) {
        message = 'No response from server';
      }
      const apiError = new Error(message);
      (apiError as unknown as Record<string, unknown>).original = error;
      return Promise.reject(apiError);
    },
  );

  return client;
}
