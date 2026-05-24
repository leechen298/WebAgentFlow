export const apiBaseUrl = process.env.E2E_API_BASE_URL ?? 'http://127.0.0.1:8001';
export const consoleBaseUrl = process.env.E2E_CONSOLE_BASE_URL ?? 'http://127.0.0.1:5174';
export const validationBaseUrl =
  process.env.WAF_FIXTURE_SITE_URL ??
  process.env.E2E_VALIDATION_BASE_URL ??
  'http://127.0.0.1:5175';

export function apiUrl(path: string): string {
  return `${apiBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
}

export function validationUrl(path: string): string {
  return `${validationBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
}

export function consoleUrl(path: string): string {
  return `${consoleBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
}
