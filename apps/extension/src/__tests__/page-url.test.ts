import { describe, expect, it } from 'vitest';
import { getCanonicalPageUrl } from '../recorder/page-url';

describe('canonical page url', () => {
  it('returns plain urls unchanged', () => {
    expect(getCanonicalPageUrl('https://example.com/path?a=1')).toBe('https://example.com/path?a=1');
  });

  it('unwraps iframe shell urls to the embedded business page', () => {
    const raw = 'https://staff.example.com/iframe?url=https%3A%2F%2Fclient.example.com%2Fluckdraw%2Fedit%3Fid%3D1';
    expect(getCanonicalPageUrl(raw)).toBe('https://client.example.com/luckdraw/edit?id=1');
  });

  it('unwraps nested iframe shells up to three levels', () => {
    const inner = encodeURIComponent('https://app.example.com/iframe?url=' + encodeURIComponent('https://target.example.com/page'));
    const outer = `https://shell.example.com/iframe?url=${inner}`;
    expect(getCanonicalPageUrl(outer)).toBe('https://target.example.com/page');
  });

  it('ignores non-iframe wrappers and malformed urls', () => {
    expect(getCanonicalPageUrl('https://shell.example.com/embed?url=https%3A%2F%2Ftarget.example.com')).toBe(
      'https://shell.example.com/embed?url=https%3A%2F%2Ftarget.example.com',
    );
    expect(getCanonicalPageUrl('not a url')).toBe('not a url');
  });
});
