import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Validation-site selector stability smoke.
 *
 * Replay E2E and page analysis depend on stable CSS selectors in
 * validation-site fixture pages. If these selectors drift, replay
 * will fail silently or with confusing errors.
 *
 * This test reads the Vue source files and verifies that critical
 * selectors (id, data-testid, role) are present. It does NOT require
 * a running server.
 */

const VS_ROOT = resolve(__dirname, '../../../../validation-site/src/pages');

function readPage(filename: string): string {
  return readFileSync(resolve(VS_ROOT, filename), 'utf-8');
}

describe('Validation-site selector stability', () => {
  // ── LoginPage.vue ─────────────────────────────────────────

  describe('LoginPage selectors', () => {
    const src = readPage('LoginPage.vue');

    it('has #username input', () => {
      expect(src).toContain('id="username"');
    });

    it('has #password input', () => {
      expect(src).toContain('id="password"');
    });

    it('has login error region with role=alert', () => {
      expect(src).toContain('role="alert"');
      expect(src).toContain('data-testid="login-error"');
    });

    it('has submit button', () => {
      expect(src).toContain('type="submit"');
    });
  });

  // ── UserDirectoryPage.vue ─────────────────────────────────

  describe('UserDirectoryPage selectors', () => {
    const src = readPage('UserDirectoryPage.vue');

    it('has #search-name input', () => {
      expect(src).toContain('id="search-name"');
    });

    it('has #search-email input', () => {
      expect(src).toContain('id="search-email"');
    });

    it('has #search-role input', () => {
      expect(src).toContain('id="search-role"');
    });

    it('has #search-status radio group', () => {
      expect(src).toContain('id="search-status"');
    });

    it('has #btn-search button', () => {
      expect(src).toContain('id="btn-search"');
    });

    it('has #btn-reset button', () => {
      expect(src).toContain('id="btn-reset"');
    });

    it('has #user-search-form', () => {
      expect(src).toContain('id="user-search-form"');
    });

    it('has data-user-id on table rows', () => {
      expect(src).toContain('data-user-id');
    });

    it('has data-testid="user-detail"', () => {
      expect(src).toContain('data-testid="user-detail"');
    });
  });

  // ── DashboardPage.vue ─────────────────────────────────────

  describe('DashboardPage selectors', () => {
    const src = readPage('DashboardPage.vue');

    it('has data-testid="dashboard-welcome"', () => {
      expect(src).toContain('data-testid="dashboard-welcome"');
    });
  });
});
