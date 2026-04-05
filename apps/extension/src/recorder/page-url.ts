/**
 * Resolve a user-facing page identity URL.
 *
 * We keep raw frame transport details in `frameInfo.frameUrl`, but normalize
 * shell iframe wrappers like:
 *   https://staff.../iframe?...&url=https%3A%2F%2Fclient.../luckdraw/edit...
 *
 * to the embedded business page URL so direct access and iframe access are
 * treated as the same page by non-technical users.
 */
export function getCanonicalPageUrl(rawUrl: string): string {
  let current = rawUrl;

  for (let i = 0; i < 3; i += 1) {
    const next = unwrapIframeShellUrl(current);
    if (!next || next === current) return current;
    current = next;
  }

  return current;
}

function unwrapIframeShellUrl(rawUrl: string): string | null {
  try {
    const url = new URL(rawUrl);
    const embedded = url.searchParams.get('url');
    if (!embedded) return null;

    const normalizedPath = url.pathname.replace(/\/+$/, '');
    const looksLikeIframeShell =
      normalizedPath.endsWith('/iframe') || normalizedPath === '/iframe';

    if (!looksLikeIframeShell) return null;

    const decoded = decodeURIComponent(embedded);
    const nested = new URL(decoded);
    if (!['http:', 'https:'].includes(nested.protocol)) return null;

    return nested.toString();
  } catch {
    return null;
  }
}
