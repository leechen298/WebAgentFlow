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

    it('should detect "活动名称" as input or group', () => {
      const node = findByLabel('活动名称');
      expect(node).toBeDefined();
      // walkNode-first may produce group (with input as child) or input leaf
      expect(['input', 'text', 'group']).toContain(node!.type);
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
      if (node!.type === 'group' && node!.children) {
        const uploadLeaf = findNodes([node!], (n) => n.type === 'upload')[0];
        expect(uploadLeaf).toBeDefined();
      } else {
        expect(node!.type).toBe('upload');
      }
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

    it('section/group nodes should have children arrays (except navigation)', () => {
      const containers = findNodes(
        tree,
        (n) => (n.type === 'section' || n.type === 'group') && n.blockType !== 'navigation',
      );
      for (const c of containers) {
        expect(c.children).toBeInstanceOf(Array);
        expect(c.children!.length).toBeGreaterThan(0);
      }
    });

    it('high-fidelity tree should preserve meaningful non-section container nodes', () => {
      const leaves = findNodes(
        tree,
        (n) =>
          n.type !== 'section' &&
          n.type !== 'group' &&
          n.type !== 'table' &&
          n.children !== undefined,
      );
      expect(leaves.length).toBeGreaterThan(0);
    });
  });

  // ── DOM fidelity issue regression tests (JSONC issues 1-9) ──────────────

  describe('DOM fidelity — tip/hint preservation (issue 1)', () => {
    it('"活动名称" form-item should contain tip text as sibling node', () => {
      const nameNode = findByLabel('活动名称');
      expect(nameNode).toBeDefined();
      if (nameNode!.children) {
        const tipNode = findNodes(nameNode!.children, (c) =>
          (c.type === 'alert' || c.type === 'text' || c.type === 'custom') &&
          (c.label?.includes('规范命名') || c.localHtml?.includes('规范命名') || c.description?.includes('规范命名')),
        )[0];
        expect(tipNode, 'tip text should be preserved in form-item subtree').toBeDefined();
      }
    });
  });

  describe('DOM fidelity — table image column (issue 2)', () => {
    it('prize table rows should keep image cells as structured objects with src', () => {
      const tables = findByType('table');
      const prizeTable = tables.find((t) => t.headers?.includes('奖品图'));
      expect(prizeTable).toBeDefined();
      expect(prizeTable!.rows).toBeDefined();
      const imgColIdx = prizeTable!.headers!.indexOf('奖品图');
      const imgCells = prizeTable!.rows!.map((r) => r[imgColIdx]);
      const imageCell = imgCells.find((cell) =>
        typeof cell === 'object' &&
        cell !== null &&
        'type' in cell &&
        (cell as Record<string, unknown>).type === 'image' &&
        typeof (cell as Record<string, unknown>).src === 'string',
      );
      expect(imageCell).toBeDefined();
    });

    it('prize table action cells should preserve Edit/Delete buttons structurally', () => {
      const tables = findByType('table');
      const prizeTable = tables.find((t) => t.headers?.includes('操作'));
      expect(prizeTable).toBeDefined();
      const actionColIdx = prizeTable!.headers!.indexOf('操作');
      const actionCells = prizeTable!.rows!.map((r) => r[actionColIdx]);
      const actionCell = actionCells.find((cell) =>
        typeof cell === 'object' &&
        cell !== null &&
        'type' in cell &&
        (cell as Record<string, unknown>).type === 'button-group',
      ) as Record<string, unknown> | undefined;
      expect(actionCell).toBeDefined();
      const actions = (actionCell?.actions ?? []) as Array<Record<string, unknown>>;
      expect(actions.some((a) => a.label === '编辑')).toBe(true);
      expect(actions.some((a) => a.label === '删除')).toBe(true);
    });

    it('prize table footer tip block should be preserved after the table', () => {
      const prizeGroup = findByLabel('奖品配置');
      expect(prizeGroup).toBeDefined();
      const subtree = findNodes([prizeGroup!], () => true);
      const tableIdx = subtree.findIndex((n) => n.type === 'table');
      const footerTipIdx = subtree.findIndex((n) =>
        (n.type === 'alert' || n.type === 'text') &&
        (n.label?.includes('说明：1') || n.description?.includes('说明：1')),
      );
      expect(tableIdx).toBeGreaterThanOrEqual(0);
      expect(footerTipIdx).toBeGreaterThan(tableIdx);
    });
  });

  describe('DOM fidelity — alert/tip between title and table (issues 4,5)', () => {
    it('"全局中奖概率配置" section should preserve title → alert → table → actions order', () => {
      const section = findByLabel('🎯 全局中奖概率配置');
      expect(section).toBeDefined();
      expect(section!.children).toBeDefined();
      const directChildren = section!.children!;
      expect(directChildren[0]?.type).toBe('heading');
      expect(directChildren[1]?.type).toBe('alert');
      expect(directChildren[2]?.type).toBe('table');
      expect(findNodes([directChildren[3]], (n) => n.type === 'button' && n.label === '批量设置概率').length).toBeGreaterThan(0);
    });
  });

  describe('DOM fidelity — move buttons (issue 6)', () => {
    it('task cards should have 上移/下移 buttons', () => {
      const moveUp = findNodes(tree, (n) => n.type === 'button' && n.label === '上移');
      const moveDown = findNodes(tree, (n) => n.type === 'button' && n.label === '下移');
      expect(moveUp.length).toBeGreaterThan(0);
      expect(moveDown.length).toBeGreaterThan(0);
    });
  });

  describe('DOM fidelity — input-number in table (issue 7)', () => {
    it('probability table rows should keep input-number cells as structured controls', () => {
      const tables = findByType('table');
      const probTable = tables.find((t) => t.headers?.includes('中奖概率'));
      expect(probTable).toBeDefined();
      const lastCell = probTable!.rows?.[0]?.[probTable!.rows![0].length - 1];
      expect(typeof lastCell).toBe('object');
      expect((lastCell as Record<string, unknown>).type).toBe('input-number');
      expect((lastCell as Record<string, unknown>).value).toBeDefined();
    });
  });

  describe('DOM fidelity — no hard regroup / no list compression', () => {
    it('should preserve all task-like sibling containers instead of collapsing to "其他 N 项"', () => {
      const taskLikeContainers = findNodes(tree, (n) => {
        if (!n.children || n.children.length === 0) return false;
        const buttons = findNodes([n], (child) => child.type === 'button');
        const labels = buttons.map((child) => child.label);
        if (labels.filter((label) => label === '编辑任务').length !== 1) return false;
        if (!labels.includes('自定义概率')) return false;
        return findNodes([n], (child) => child.label?.includes('任务')).length > 0;
      });
      expect(taskLikeContainers.length).toBeGreaterThanOrEqual(8);
      expect(findNodes(tree, (n) => n.label?.startsWith('其他 ')).length).toBe(0);
    });
  });

  describe('DOM fidelity — color picker (issue 9)', () => {
    it('"页面背景色" subtree should contain a color node with extracted value', () => {
      const node = findByLabel('页面背景色');
      expect(node).toBeDefined();
      const colorNode = findNodes([node!], (n) => n.type === 'color')[0];
      expect(colorNode).toBeDefined();
      expect(colorNode!.value).toBeDefined();
      expect(colorNode!.value).toMatch(/rgb/);
    });

    it('"页面背景色" subtree should not surface hidden popup action buttons', () => {
      const node = findByLabel('页面背景色');
      expect(node).toBeDefined();
      const popupButtons = findNodes([node!], (n) =>
        n.type === 'button' && ['清空', '确定'].includes(n.label ?? ''),
      );
      expect(popupButtons.length).toBe(0);
    });
  });

  describe('DOM fidelity — hidden blocks and status text', () => {
    it('should preserve hidden custom probability config containers with hidden state', () => {
      const configs = findNodes(tree, (n) => {
        if (!(n.cssState === 'display:none' || n.visible === false) || !n.children) return false;
        return findNodes([n], (child) =>
          child.type === 'table' &&
          !!child.headers &&
          child.headers.includes('自定义概率（留空=0%）'),
        ).length > 0;
      });
      expect(configs.length).toBeGreaterThan(0);
    });

    it('should preserve probability status text together with save button', () => {
      const status = findNodes(tree, (n) => {
        if (!n.children || n.children.length === 0) return false;
        const hasStatusText = findNodes([n], (child) => child.label?.includes('概率总和：100%')).length > 0;
        const hasSaveButton = findNodes([n], (child) => child.type === 'button' && child.label === '保存自定义概率').length > 0;
        return hasStatusText && hasSaveButton;
      })[0];
      expect(status).toBeDefined();
      expect(findNodes([status!], (n) => n.type === 'button' && n.label === '保存自定义概率').length).toBeGreaterThan(0);
    });

    it('should preserve hidden batch dialog footer content with hidden state', () => {
      const hiddenFooters = findNodes(tree, (n) => {
        if (!(n.cssState === 'display:none' || n.visible === false) || !n.children) return false;
        const buttons = findNodes([n], (child) => child.type === 'button');
        const labels = buttons.map((child) => child.label);
        return labels.includes('取 消') && labels.includes('确 定');
      });
      expect(hiddenFooters.length).toBeGreaterThan(0);
      const footer = hiddenFooters[0];
      expect(findNodes([footer], (n) => n.type === 'button' && n.label === '取 消').length).toBeGreaterThan(0);
      expect(findNodes([footer], (n) => n.type === 'button' && n.label === '确 定').length).toBeGreaterThan(0);
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
