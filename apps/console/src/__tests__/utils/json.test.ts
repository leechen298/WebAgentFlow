import { describe, it, expect } from 'vitest';
import { safeParseJson, formatJsonString, isValidJson } from '@/utils/json';

describe('JSON Utils', () => {
  describe('safeParseJson', () => {
    it('should parse valid JSON successfully', () => {
      const json = '{"name": "test", "value": 123}';
      const result = safeParseJson(json);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual({ name: 'test', value: 123 });
      }
    });

    it('should handle empty string', () => {
      const result = safeParseJson('');
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual({});
      }
    });

    it('should handle whitespace only string', () => {
      const result = safeParseJson('   \n  \t  ');
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual({});
      }
    });

    it('should return error for invalid JSON', () => {
      const result = safeParseJson('{invalid json}');
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBeDefined();
      }
    });

    it('should parse array JSON', () => {
      const json = '[1, 2, 3, "test"]';
      const result = safeParseJson<number[]>(json);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual([1, 2, 3, 'test']);
      }
    });
  });

  describe('formatJsonString', () => {
    it('should format JSON object with indentation', () => {
      const obj = { name: 'test', value: 123 };
      const result = formatJsonString(obj);

      expect(result).toBe('{\n  "name": "test",\n  "value": 123\n}');
    });

    it('should return empty string for null', () => {
      expect(formatJsonString(null)).toBe('');
    });

    it('should return empty string for undefined', () => {
      expect(formatJsonString(undefined)).toBe('');
    });

    it('should stringify primitives', () => {
      expect(formatJsonString('string')).toBe('"string"');
      expect(formatJsonString(123)).toBe('123');
      expect(formatJsonString(true)).toBe('true');
    });

    it('should handle circular references gracefully', () => {
      const obj: Record<string, unknown> = { name: 'test' };
      obj.self = obj;
      const result = formatJsonString(obj);
      expect(result).toBe('[object Object]');
    });
  });

  describe('isValidJson', () => {
    it('should return true for valid JSON', () => {
      expect(isValidJson('{"name": "test"}')).toBe(true);
      expect(isValidJson('[1, 2, 3]')).toBe(true);
    });

    it('should return true for empty string', () => {
      expect(isValidJson('')).toBe(true);
    });

    it('should return true for whitespace only', () => {
      expect(isValidJson('   \n  ')).toBe(true);
    });

    it('should return false for invalid JSON', () => {
      expect(isValidJson('{invalid}')).toBe(false);
      expect(isValidJson('{"name": test}')).toBe(false);
    });
  });
});
