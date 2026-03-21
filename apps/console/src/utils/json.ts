/**
 * Safely parse JSON string
 */
export function safeParseJson<T = unknown>(jsonString: string): { success: true; data: T } | { success: false; error: string } {
  if (!jsonString.trim()) {
    return { success: true, data: {} as T };
  }
  try {
    const data = JSON.parse(jsonString) as T;
    return { success: true, data };
  } catch (e) {
    const error = e instanceof Error ? e.message : 'Invalid JSON';
    return { success: false, error };
  }
}

/**
 * Safely stringify JSON with indentation
 */
export function formatJsonString(obj: unknown): string {
  if (obj === null || obj === undefined) {
    return '';
  }
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

/**
 * Validate JSON string
 */
export function isValidJson(jsonString: string): boolean {
  if (!jsonString.trim()) {
    return true;
  }
  try {
    JSON.parse(jsonString);
    return true;
  } catch {
    return false;
  }
}
