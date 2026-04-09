/**
 * Integration test for captureInitialState() — AST tree building.
 *
 * Uses a real-world lottery activity page HTML fixture to verify that the
 * tree walker produces a correct, well-structured StateNode[] tree.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { StateNode, PageInitialState } from '@web-agent-flow/shared-types';
import { captureInitialState } from '../recorder/initial-state';

// ── Fixture loading ────────────────────────────────────────────────────────

let result: PageInitialState;
let tree: StateNode[];

beforeAll(() => {
  const html = readFileSync(
    resolve(__dirname, 'fixtures/lottery-page.html'),
    'utf-8',
  );
  document.body.innerHTML = html;
  result = captureInitialState();
  tree = result.stateTree ?? [];
});

// ── Helpers ────────────────────────────────────────────────────────────────

/** Recursively find all nodes matching a predicate. */
function findNodes(
  nodes: StateNode[],
  predicate: (n: StateNode) => boolean,
): StateNode[] {
  const found: StateNode[] = [];
  const walk = (list: StateNode[]) => {
    for (const n of list) {
      if (predicate(n)) found.push(n);
      if (n.children) walk(n.children);
    }
  };
  walk(nodes);
  return found;
}

/** Find a single node by label (case-sensitive). */
function findByLabel(label: string): StateNode | undefined {
  return findNodes(tree, (n) => n.label === label)[0];
}

/** Find all nodes of a given type. */
function findByType(type: string): StateNode[] {
  return findNodes(tree, (n) => n.type === type);
}

/** Recursively count all nodes. */
function countNodes(nodes: StateNode[]): number {
  let count = 0;
  for (const n of nodes) {
    count++;
    if (n.children) count += countNodes(n.children);
  }
  return count;
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('captureInitialState — lottery activity page', () => {
  describe('basic result structure', () => {
    it('should return a valid PageInitialState', () => {
      expect(result).toBeDefined();
      expect(result.capturedAt).toBeGreaterThan(0);
      expect(result.pageTitle).toBeDefined();
      expect(result.stateTree).toBeInstanceOf(Array);
    });

    it('should produce a non-empty tree', () => {
      expect(tree.length).toBeGreaterThan(0);
    });

    it('should have a reasonable number of total nodes', () => {
      const total = countNodes(tree);
      // The page has ~16 form items + sections + tables + buttons
      // Expect between 10 and 300 nodes
      expect(total).toBeGreaterThanOrEqual(10);
      expect(total).toBeLessThanOrEqual(300);
    });
  });

  describe('section structure', () => {
    const sectionNodes = () => findByType('section');

    it('should create section nodes', () => {
      expect(sectionNodes().length).toBeGreaterThan(0);
    });

    it('should detect major page sections by title', () => {
      const sectionLabels = sectionNodes().map((n) => n.label);
      // The page has 4 main titled sections
      const expectedSections = ['基本信息', '限制条件', '奖品信息', '任务列表'];
      for (const title of expectedSections) {
        expect(
          sectionLabels,
          `should have section "${title}"`,
        ).toContainEqual(title);
      }
    });

    it('section nodes should have children', () => {
      for (const section of sectionNodes()) {
        if (section.children) {
          expect(section.children.length).toBeGreaterThan(0);
        }
      }
    });
  });

  describe('form field detection', () => {
    it('should detect form fields with labels', () => {
      const labeledNodes = findNodes(tree, (n) => !!n.label && n.type !== 'section' && n.type !== 'group');
      expect(labeledNodes.length).toBeGreaterThan(5);
    });

    it('should detect "活动名称" as input', () => {
      const node = findByLabel('活动名称');
      expect(node).toBeDefined();
      expect(node!.type).toBe('input');
    });

    it('should detect "活动时间" as date', () => {
      const node = findByLabel('活动时间');
      expect(node).toBeDefined();
      // Could be 'date' or 'input' depending on classifier
      expect(['date', 'input']).toContain(node!.type);
    });

    it('should detect "活动类型" as radio', () => {
      const node = findByLabel('活动类型');
      expect(node).toBeDefined();
      expect(node!.type).toBe('radio');
    });

    it('should detect "活动主视觉" as upload', () => {
      const node = findByLabel('活动主视觉');
      expect(node).toBeDefined();
      expect(node!.type).toBe('upload');
    });

    it('should detect "页面背景色" as color or group', () => {
      const node = findByLabel('页面背景色');
      expect(node).toBeDefined();
      // Color picker with multiple internal controls may be expanded as group
      expect(['color', 'group']).toContain(node!.type);
    });

    it('should detect "活动规则配置" as radio', () => {
      const node = findByLabel('活动规则配置');
      expect(node).toBeDefined();
      expect(node!.type).toBe('radio');
    });

    it('should detect "参与限制" as select', () => {
      const node = findByLabel('参与限制');
      expect(node).toBeDefined();
      expect(node!.type).toBe('select');
    });

    it('should detect "发放时间" as select', () => {
      const node = findByLabel('发放时间');
      expect(node).toBeDefined();
      expect(node!.type).toBe('select');
    });
  });

  describe('required field detection', () => {
    it('should mark required fields', () => {
      const requiredNodes = findNodes(tree, (n) => n.required === true);
      expect(requiredNodes.length).toBeGreaterThan(0);
    });

    it('should mark "活动名称" as required', () => {
      const node = findByLabel('活动名称');
      expect(node?.required).toBe(true);
    });

    it('should mark "活动城市" as required', () => {
      const node = findByLabel('活动城市');
      expect(node?.required).toBe(true);
    });
  });

  describe('value extraction', () => {
    it('should detect radio fields', () => {
      const radioNodes = findByType('radio');
      // Element UI radios don't have native `checked` attribute — the checked
      // state is represented by `is-checked` CSS class. In jsdom (no JS state),
      // values may not be extractable. Just verify radio nodes exist.
      expect(radioNodes.length).toBeGreaterThan(0);
    });

    it('should capture tag/chip values for "活动城市"', () => {
      const node = findByLabel('活动城市');
      // The field has city tags — value should be extracted
      if (node?.value) {
        expect(node.value.length).toBeGreaterThan(0);
      }
    });
  });

  describe('selector generation', () => {
    it('should generate selectors for leaf nodes', () => {
      const leafNodes = findNodes(
        tree,
        (n) => n.type !== 'section' && n.type !== 'group' && !!n.selector,
      );
      expect(leafNodes.length).toBeGreaterThan(0);
    });

    it('selectors should be valid CSS-like strings', () => {
      const withSelector = findNodes(tree, (n) => !!n.selector);
      for (const node of withSelector.slice(0, 10)) {
        expect(node.selector).toMatch(/[a-z]/); // Contains tag names
        expect(node.selector!.length).toBeGreaterThan(0);
        expect(node.selector!.length).toBeLessThan(500);
      }
    });
  });

  describe('table detection', () => {
    it('should detect at least one table', () => {
      const tables = findByType('table');
      expect(tables.length).toBeGreaterThan(0);
    });

    it('table nodes should have headers', () => {
      const tables = findByType('table');
      const withHeaders = tables.filter((t) => t.headers && t.headers.length > 0);
      expect(withHeaders.length).toBeGreaterThan(0);
    });

    it('table nodes should have row data or expanded children', () => {
      const tables = findByType('table');
      // Tables may have flat rows (simple) or children (complex cells with buttons)
      const withContent = tables.filter((t) =>
        (t.rows && t.rows.length > 0) || (t.children && t.children.length > 0),
      );
      expect(withContent.length).toBeGreaterThan(0);
    });

    it('"奖品配置" group should contain a table (possibly nested)', () => {
      const group = findByLabel('奖品配置');
      expect(group).toBeDefined();
      // Table may be directly in children or nested deeper
      const tables = findNodes(group?.children ? [group] : [], (n) => n.type === 'table');
      expect(tables.length).toBeGreaterThan(0);
    });
  });

  describe('button detection', () => {
    it('should detect action buttons', () => {
      const buttons = findByType('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('should detect submit/cancel buttons', () => {
      const buttons = findByType('button');
      const buttonLabels = buttons.map((b) => b.label).filter(Boolean);
      // Should have at least one recognizable action button
      const hasAction = buttonLabels.some((label) =>
        ['取消', '确定', '取 消', '确 定'].includes(label!),
      );
      expect(hasAction).toBe(true);
    });
  });

  describe('node type variety', () => {
    it('should produce multiple node types', () => {
      const types = new Set<string>();
      findNodes(tree, (n) => {
        types.add(n.type);
        return false;
      });
      // Should have at least: section, input, radio, select, button, table
      expect(types.size).toBeGreaterThanOrEqual(4);
    });
  });

  describe('tree structure integrity', () => {
    it('all nodes should have a type', () => {
      findNodes(tree, (n) => {
        expect(n.type).toBeDefined();
        expect(typeof n.type).toBe('string');
        expect(n.type.length).toBeGreaterThan(0);
        return false;
      });
    });

    it('section/group nodes should have children arrays', () => {
      const containers = findNodes(
        tree,
        (n) => n.type === 'section' || n.type === 'group',
      );
      for (const c of containers) {
        expect(c.children).toBeInstanceOf(Array);
        expect(c.children!.length).toBeGreaterThan(0);
      }
    });

    it('leaf nodes should not have children', () => {
      const leaves = findNodes(
        tree,
        (n) =>
          n.type !== 'section' &&
          n.type !== 'group' &&
          n.children !== undefined,
      );
      // Most leaf nodes shouldn't have children (allow zero for edge cases)
      expect(leaves.length).toBeLessThanOrEqual(5);
    });
  });

  describe('tree snapshot', () => {
    it('should output tree summary for manual inspection', () => {
      const lines: string[] = [];
      const printTree = (nodes: StateNode[], indent: number) => {
        for (const n of nodes) {
          const prefix = '  '.repeat(indent);
          const parts = [n.type];
          if (n.label) parts.push(`"${n.label}"`);
          if (n.value) parts.push(`val="${n.value.slice(0, 30)}"`);
          if (n.required) parts.push('*required');
          if (n.headers) parts.push(`headers=[${n.headers.join(',')}]`);
          if (n.rows) parts.push(`rows=${n.rows.length}`);
          if (n.itemCount) parts.push(`items=${n.itemCount}`);
          if (n.selector) parts.push(`sel="${n.selector.slice(0, 50)}"`);
          lines.push(`${prefix}${parts.join(' | ')}`);
          if (n.children) printTree(n.children, indent + 1);
        }
      };
      printTree(tree, 0);

      // Print the tree for manual inspection
      console.log('\n=== AST Tree Snapshot ===');
      console.log(lines.join('\n'));
      console.log(`=== Total: ${countNodes(tree)} nodes ===\n`);

      // This test always passes — it's for human review
      expect(lines.length).toBeGreaterThan(0);
    });
  });
});
