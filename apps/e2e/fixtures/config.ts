export const apiBaseUrl = process.env.E2E_API_BASE_URL ?? 'http://127.0.0.1:8001';
export const consoleBaseUrl = process.env.E2E_CONSOLE_BASE_URL ?? 'http://127.0.0.1:5174';
export const fixtureBaseUrl =
  process.env.WAF_FIXTURE_SITE_URL ??
  process.env.E2E_FIXTURE_BASE_URL ??
  '';

export function apiUrl(path: string): string {
  return `${apiBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
}

export function fixtureUrl(path: string): string {
  if (!fixtureBaseUrl) {
    throw new Error('Set WAF_FIXTURE_SITE_URL or E2E_FIXTURE_BASE_URL.');
  }
  return `${fixtureBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
}

export function consoleUrl(path: string): string {
  return `${consoleBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
}
