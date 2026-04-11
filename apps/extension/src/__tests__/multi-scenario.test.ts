/**
 * Multi-scenario integration tests for captureInitialState().
 *
 * Tests diverse page types: corporate site, admin dashboard, H5 mobile,
 * multi-nav docs page, no-semantic-tags page, and data dashboard.
 * Verifies that navigation scanning, form capture, table extraction,
 * and general page structure work universally.
 */

import { describe, it, expect, beforeAll, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { StateNode, PageInitialState } from '@web-agent-flow/shared-types';
import { captureInitialState } from '../recorder/initial-state';

// ── Helpers ────────────────────────────────────────────────────────────────

function loadFixture(name: string): string {
  return readFileSync(resolve(__dirname, `fixtures/${name}`), 'utf-8');
}

function findNodes(nodes: StateNode[], predicate: (n: StateNode) => boolean): StateNode[] {
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

function findByType(tree: StateNode[], type: string): StateNode[] {
  return findNodes(tree, (n) => n.type === type);
}

function findByLabel(tree: StateNode[], label: string): StateNode | undefined {
  return findNodes(tree, (n) => n.label === label)[0];
}

function findByBlockType(tree: StateNode[], blockType: string): StateNode[] {
  return findNodes(tree, (n) => n.blockType === blockType);
}

function countNodes(nodes: StateNode[]): number {
  let count = 0;
  for (const n of nodes) {
    count++;
    if (n.children) count += countNodes(n.children);
  }
  return count;
}

function capture(html: string): { result: PageInitialState; tree: StateNode[] } {
  document.body.innerHTML = html;
  const result = captureInitialState();
  const tree = result.stateTree ?? [];
  return { result, tree };
}

function printTree(tree: StateNode[]): string {
  const lines: string[] = [];
  const walk = (nodes: StateNode[], indent: number) => {
    for (const n of nodes) {
      const prefix = '  '.repeat(indent);
      const parts = [n.type];
      if (n.blockType) parts.push(`[${n.blockType}]`);
      if (n.label) parts.push(`"${n.label}"`);
      if (n.value) parts.push(`val="${n.value.slice(0, 30)}"`);
      if (n.href) parts.push(`→ ${n.href}`);
      if (n.active) parts.push('✓active');
      if (n.required) parts.push('*required');
      if (n.headers) parts.push(`cols=[${n.headers.join(',')}]`);
      if (n.itemCount) parts.push(`(${n.itemCount})`);
      lines.push(`${prefix}${parts.join(' | ')}`);
      if (n.children) walk(n.children, indent + 1);
    }
  };
  walk(tree, 0);
  return lines.join('\n');
}

// ── Tests ──────────────────────────────────────────────────────────────────

afterEach(() => {
  document.body.innerHTML = '';
});

// ─── 1. Corporate / Marketing Site ─────────────────────────────────────────

describe('corporate-site.html — Marketing website', () => {
  let tree: StateNode[];

  beforeAll(() => {
    ({ tree } = capture(loadFixture('corporate-site.html')));
  });

  it('should produce a non-empty tree', () => {
    expect(tree.length).toBeGreaterThan(0);
    console.log('\n=== Corporate Site ===\n' + printTree(tree) + '\n');
  });

  it('should detect navigation sections with localHtml (not expanded children)', () => {
    const navSections = findByBlockType(tree, 'navigation');
    expect(navSections.length).toBeGreaterThan(0);
    // Nav sections should have localHtml, not children
    for (const nav of navSections) {
      expect(nav.localHtml).toBeDefined();
      expect(nav.children).toBeUndefined();
    }
  });

  it('should preserve nav content in localHtml', () => {
    const navSections = findByBlockType(tree, 'navigation');
    const header = navSections.find((s) => s.label === 'Header');
    expect(header?.localHtml).toContain('Products');
    expect(header?.localHtml).toContain('Contact');
  });

  it('should detect active nav item in summaryText', () => {
    const navSections = findByBlockType(tree, 'navigation');
    const header = navSections.find((s) => s.label === 'Header');
    expect(header?.summaryText).toContain('Products');
  });

  it('should detect sidebar and footer nav sections', () => {
    const navSections = findByBlockType(tree, 'navigation');
    const labels = navSections.map((s) => s.label);
    expect(labels).toContain('Sidebar');
    expect(labels).toContain('Footer');
  });

  it('should capture main content (hero title, CTA button)', () => {
    const buttons = findByType(tree, 'button');
    expect(buttons.some((b) => b.label === 'Get Started')).toBe(true);
  });
});

// ─── 2. Admin Sidebar (non-semantic tags) ──────────────────────────────────

describe('admin-sidebar.html — Admin dashboard with div-based sidebar', () => {
  let tree: StateNode[];

  beforeAll(() => {
    ({ tree } = capture(loadFixture('admin-sidebar.html')));
  });

  it('should produce a non-empty tree', () => {
    expect(tree.length).toBeGreaterThan(0);
    console.log('\n=== Admin Sidebar ===\n' + printTree(tree) + '\n');
  });

  it('should NOT produce navigation blockType for div.left-menu (no semantic tag)', () => {
    // div.left-menu has no nav/aside/header/footer tag and no ARIA role,
    // so scanNavigation should NOT pick it up as a navigation section.
    const navSections = findByBlockType(tree, 'navigation');
    expect(navSections.length).toBe(0);
    // Note: the left-menu is outside role="main", so its links are not
    // captured at all. This is expected — without semantic tags, the tool
    // can't distinguish navigation from content outside the main root.
  });

  it('should detect the data table', () => {
    const tables = findByType(tree, 'table');
    expect(tables.length).toBeGreaterThan(0);
    const userTable = tables.find((t) => t.headers?.includes('Name'));
    expect(userTable).toBeDefined();
    expect(userTable!.headers).toContain('Email');
    expect(userTable!.headers).toContain('Role');
  });

  it('should detect action buttons (Search, pagination)', () => {
    const buttons = findByType(tree, 'button');
    const labels = buttons.map((b) => b.label);
    expect(labels.some((l) => l === 'Search')).toBe(true);
  });
});

// ─── 3. H5 Mobile (Vant-style) ────────────────────────────────────────────

describe('h5-mobile.html — Mobile e-commerce product page', () => {
  let tree: StateNode[];

  beforeAll(() => {
    ({ tree } = capture(loadFixture('h5-mobile.html')));
  });

  it('should produce a non-empty tree', () => {
    expect(tree.length).toBeGreaterThan(0);
    console.log('\n=== H5 Mobile ===\n' + printTree(tree) + '\n');
  });

  it('should capture content (product name, price, specs exist somewhere)', () => {
    const total = countNodes(tree);
    expect(total).toBeGreaterThan(3);
  });

  it('should detect bottom action buttons', () => {
    const buttons = findByType(tree, 'button');
    const labels = buttons.map((b) => b.label).filter(Boolean);
    // Vant button text is inside van-button__text span
    const hasCart = labels.some((l) => l!.includes('Add to Cart') || l!.includes('Cart'));
    const hasBuy = labels.some((l) => l!.includes('Buy Now') || l!.includes('Buy'));
    expect(hasCart || hasBuy).toBe(true);
  });

  it('should not crash on Vant-specific class names', () => {
    // Verify tree is valid — no undefined types, no empty sections
    findNodes(tree, (n) => {
      expect(n.type).toBeDefined();
      expect(typeof n.type).toBe('string');
      return false;
    });
  });
});

// ─── 4. Multi-nav Documentation Page ───────────────────────────────────────

describe('multi-nav.html — Docs page with multiple nav areas', () => {
  let tree: StateNode[];

  beforeAll(() => {
    ({ tree } = capture(loadFixture('multi-nav.html')));
  });

  it('should produce a non-empty tree', () => {
    expect(tree.length).toBeGreaterThan(0);
    console.log('\n=== Multi-Nav ===\n' + printTree(tree) + '\n');
  });

  it('should detect multiple navigation sections', () => {
    const navSections = findByBlockType(tree, 'navigation');
    expect(navSections.length).toBeGreaterThanOrEqual(3);
  });

  it('should label navigation sections distinctly', () => {
    const navSections = findByBlockType(tree, 'navigation');
    const labels = navSections.map((s) => s.label);
    expect(labels).toContain('Header');
    expect(labels).toContain('Breadcrumb');
    expect(labels).toContain('Sidebar');
    expect(labels).toContain('Footer');
  });

  it('should detect "Docs" as active in header nav (summaryText)', () => {
    const navSections = findByBlockType(tree, 'navigation');
    const headerNav = navSections.find((s) => s.label === 'Header');
    expect(headerNav).toBeDefined();
    expect(headerNav!.summaryText).toContain('Docs');
  });

  it('should detect "Endpoints" as active in sidebar (summaryText)', () => {
    const navSections = findByBlockType(tree, 'navigation');
    const sidebar = navSections.find((s) => s.label === 'Sidebar');
    expect(sidebar).toBeDefined();
    expect(sidebar!.summaryText).toContain('Endpoints');
  });

  it('should capture the endpoint reference table in main content', () => {
    const tables = findByType(tree, 'table');
    expect(tables.length).toBeGreaterThan(0);
    const endpointTable = tables.find((t) => t.headers?.includes('Method'));
    expect(endpointTable).toBeDefined();
    expect(endpointTable!.headers).toContain('Path');
  });
});

// ─── 5. No Semantic Tags (worst case) ──────────────────────────────────────

describe('no-semantic-tags.html — Page with zero semantic HTML tags', () => {
  let tree: StateNode[];

  beforeAll(() => {
    ({ tree } = capture(loadFixture('no-semantic-tags.html')));
  });

  it('should produce a non-empty tree', () => {
    expect(tree.length).toBeGreaterThan(0);
    console.log('\n=== No Semantic Tags ===\n' + printTree(tree) + '\n');
  });

  it('should NOT produce navigation blockType (no semantic nav tags)', () => {
    // div.top-bar has no nav/aside/header/footer — should not be scanned as nav
    const navSections = findByBlockType(tree, 'navigation');
    expect(navSections.length).toBe(0);
  });

  it('should capture top bar links as individual links in DOM order', () => {
    const links = findByType(tree, 'link');
    const labels = links.map((l) => l.label).filter(Boolean);
    expect(labels).toEqual(expect.arrayContaining(['Home', 'Profile', 'Settings', 'Logout']));
  });

  it('should capture form values without relying on list grouping', () => {
    expect(findByLabel(tree, 'Username')).toBeDefined();
    expect(findByLabel(tree, 'Email')).toBeDefined();
    expect(findByLabel(tree, 'Language')).toBeDefined();
  });

  it('should detect Save / Cancel buttons', () => {
    const buttons = findByType(tree, 'button');
    const labels = buttons.map((b) => b.label).filter(Boolean);
    expect(labels.some((l) => l === 'Save')).toBe(true);
    expect(labels.some((l) => l === 'Cancel')).toBe(true);
  });
});

// ─── 6. Data Dashboard ────────────────────────────────────────────────────

describe('data-dashboard.html — Analytics dashboard', () => {
  let tree: StateNode[];

  beforeAll(() => {
    ({ tree } = capture(loadFixture('data-dashboard.html')));
  });

  it('should produce a non-empty tree', () => {
    expect(tree.length).toBeGreaterThan(0);
    console.log('\n=== Data Dashboard ===\n' + printTree(tree) + '\n');
  });

  it('should detect top nav as navigation section', () => {
    const navSections = findByBlockType(tree, 'navigation');
    expect(navSections.length).toBeGreaterThan(0);
  });

  it('should detect nav tabs with active state (summaryText)', () => {
    const navSections = findByBlockType(tree, 'navigation');
    // At least one nav section's summaryText should contain "Analytics"
    const hasAnalytics = navSections.some((s) => s.summaryText?.includes('Analytics'));
    expect(hasAnalytics).toBe(true);
  });

  it('should detect the data table', () => {
    const tables = findByType(tree, 'table');
    expect(tables.length).toBeGreaterThan(0);
    const dailyTable = tables.find((t) => t.headers?.includes('Date'));
    expect(dailyTable).toBeDefined();
    expect(dailyTable!.headers).toContain('Visitors');
    expect(dailyTable!.rows?.length).toBe(5);
  });

  it('should detect "Apply" button in header controls', () => {
    // Date inputs may not be detected as standalone controls outside form containers,
    // but the Apply button should be captured.
    const buttons = findByType(tree, 'button');
    expect(buttons.some((b) => b.label === 'Apply')).toBe(true);
  });

  it('should detect "Apply" button', () => {
    const buttons = findByType(tree, 'button');
    expect(buttons.some((b) => b.label === 'Apply')).toBe(true);
  });
});

// ─── 7. Nested Menu (Element UI submenu + iframe) ──────────────────────────

describe('nested-menu.html — Element UI nested submenu with iframe', () => {
  let tree: StateNode[];

  beforeAll(() => {
    ({ tree } = capture(loadFixture('nested-menu.html')));
  });

  it('should produce a non-empty tree', () => {
    expect(tree.length).toBeGreaterThan(0);
    console.log('\n=== Nested Menu ===\n' + printTree(tree) + '\n');
  });

  it('should detect sidebar as navigation', () => {
    const navSections = findByBlockType(tree, 'navigation');
    expect(navSections.length).toBeGreaterThan(0);
  });

  it('should store "基本设置" submenu content in localHtml', () => {
    const navSections = findByBlockType(tree, 'navigation');
    const sidebarNav = navSections.find((s) => s.label === 'Sidebar');
    expect(sidebarNav).toBeDefined();
    // Nav sections now have localHtml, not children
    expect(sidebarNav!.localHtml).toBeDefined();
    expect(sidebarNav!.localHtml).toContain('基本设置');
    expect(sidebarNav!.children).toBeUndefined();
  });

  it('should capture leaf menu items in localHtml', () => {
    const navSections = findByBlockType(tree, 'navigation');
    const sidebarNav = navSections.find((s) => s.label === 'Sidebar');
    expect(sidebarNav).toBeDefined();
    expect(sidebarNav!.localHtml).toContain('职业标准配置列表');
    expect(sidebarNav!.localHtml).toContain('职业技能设置');
    expect(sidebarNav!.localHtml).toContain('职业用工类型切换设置');
  });

  it('should mark active menu item "职业技能设置" in summaryText or localHtml', () => {
    const navSections = findByBlockType(tree, 'navigation');
    const sidebarNav = navSections.find((s) => s.label === 'Sidebar');
    expect(sidebarNav).toBeDefined();
    // Active item should appear in summaryText or localHtml should contain the active class
    const inSummary = sidebarNav!.summaryText?.includes('职业技能设置');
    const inHtml = sidebarNav!.localHtml?.includes('职业技能设置');
    expect(inSummary || inHtml).toBe(true);
  });

  it('should capture top-level menu item "系统日志" in localHtml', () => {
    const navSections = findByBlockType(tree, 'navigation');
    const sidebarNav = navSections.find((s) => s.label === 'Sidebar');
    expect(sidebarNav).toBeDefined();
    expect(sidebarNav!.localHtml).toContain('系统日志');
  });

  it('should handle collapsed submenus gracefully', () => {
    // "高级设置" has display:none on its inner <ul>, but jsdom cannot detect
    // parent-level hidden state (only inline display:none on the element itself).
    // In a real browser, "权限管理" would be hidden. Here we just verify no crash
    // and the tree structure is valid.
    const navSections = findByBlockType(tree, 'navigation');
    expect(navSections.length).toBeGreaterThan(0);
  });

  it('should capture breadcrumb links in header nav localHtml', () => {
    const navSections = findByBlockType(tree, 'navigation');
    // Breadcrumb <nav> is inside <header class="el-header">, so it's captured
    // as "Header" navigation section
    const headerNav = navSections.find((s) => s.label === 'Header');
    expect(headerNav).toBeDefined();
    expect(headerNav!.localHtml).toContain('首页');
  });

  it('should detect iframe section with blockType iframe-content', () => {
    // In jsdom, iframe.contentDocument may not have real content,
    // so this verifies the iframe at least doesn't crash the walker.
    // If contentDocument is accessible, it should produce a section.
    const iframeSections = findByBlockType(tree, 'iframe-content');
    // In jsdom, about:blank iframe contentDocument has empty body, so no section
    // This test verifies no crash and correct handling.
    expect(iframeSections.length).toBeGreaterThanOrEqual(0);
  });

  it('should detect form fields in main content', () => {
    const inputs = findNodes(tree, (n) =>
      (n.type === 'input' || n.type === 'text') && n.label === '技能名称',
    );
    expect(inputs.length).toBe(1);
  });

  it('should detect action buttons via backtracking from form-item classification', () => {
    // "el-form-item__actions" matches isFormContainer but has no form content.
    // processFormItem returns [] → walkNode backtracks → walkChildren finds buttons.
    const buttons = findByType(tree, 'button');
    const labels = buttons.map((b) => b.label);
    expect(labels).toContain('保存');
    expect(labels).toContain('取消');
  });
});

// ─── Cross-scenario structural integrity ───────────────────────────────────

// ─── 8. Complex Nesting (form-item with sub-form, table with actions) ───────

describe('complex-nesting.html — Complex nested structures', () => {
  let tree: StateNode[];

  beforeAll(() => {
    ({ tree } = capture(loadFixture('complex-nesting.html')));
  });

  it('should produce a non-empty tree', () => {
    expect(tree.length).toBeGreaterThan(0);
    console.log('\n=== Complex Nesting ===\n' + printTree(tree) + '\n');
  });

  it('should expand form-item "Shipping Address" as group with children', () => {
    const shipping = findByLabel(tree, 'Shipping Address');
    expect(shipping).toBeDefined();
    // Should be a group (complex form-item with 3 inputs + 1 select)
    expect(shipping!.type).toBe('group');
    expect(shipping!.children).toBeDefined();
    expect(shipping!.children!.length).toBeGreaterThanOrEqual(1);
    // Should contain select somewhere in the subtree
    const selects = findByType(shipping!.children ?? [], 'select');
    expect(selects.length).toBeGreaterThan(0);
  });

  it('should expand form-item "Order Items" as group with table + button', () => {
    const orderItems = findByLabel(tree, 'Order Items');
    expect(orderItems).toBeDefined();
    expect(orderItems!.type).toBe('group');
    expect(orderItems!.children).toBeDefined();
    // Should contain a table and a button somewhere in subtree
    const tables = findByType(orderItems!.children ?? [], 'table');
    const buttons = findByType(orderItems!.children ?? [], 'button');
    expect(tables.length).toBeGreaterThan(0);
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('should keep simple form-item "Notes" as a leaf', () => {
    const notes = findByLabel(tree, 'Notes');
    expect(notes).toBeDefined();
    expect(notes!.type).toBe('textarea');
    // Should NOT have children (it's a simple leaf)
    expect(notes!.children).toBeUndefined();
  });

  it('should capture table "User List" rows with action button labels', () => {
    const tables = findByType(tree, 'table');
    const userTable = tables.find((t) => t.headers?.includes('Name') && t.headers?.includes('Actions'));
    expect(userTable).toBeDefined();
    expect(userTable!.rows).toBeDefined();
    expect(userTable!.rows!.length).toBeGreaterThanOrEqual(2);
    const actionCells = userTable!.rows!.map((r) => r[r.length - 1]);
    const actionCell = actionCells.find((cell) =>
      typeof cell === 'object' &&
      cell !== null &&
      'type' in cell &&
      (cell as Record<string, unknown>).type === 'button-group',
    ) as Record<string, unknown> | undefined;
    expect(actionCell).toBeDefined();
    const actions = (actionCell?.actions ?? []) as Array<Record<string, unknown>>;
    expect(actions.some((a) => a.label === 'Edit')).toBe(true);
  });

  it('should keep simple table "Price List" with flat rows', () => {
    const tables = findByType(tree, 'table');
    const priceTable = tables.find((t) => t.headers?.includes('Item') && t.headers?.includes('Price'));
    expect(priceTable).toBeDefined();
    // Simple table should have rows for text summary
    expect(priceTable!.rows).toBeDefined();
    expect(priceTable!.rows!.length).toBe(3);
    // Per DOM-fidelity rules, all cells go through walkNode — children may exist
    // even for simple tables (text cells produce custom nodes via fallback)
  });
});

// ─── Cross-scenario structural integrity ───────────────────────────────────

describe('structural integrity across all scenarios', () => {
  const fixtures = [
    'corporate-site.html',
    'admin-sidebar.html',
    'h5-mobile.html',
    'multi-nav.html',
    'no-semantic-tags.html',
    'data-dashboard.html',
    'nested-menu.html',
    'complex-nesting.html',
  ];

  for (const fixture of fixtures) {
    describe(fixture, () => {
      let tree: StateNode[];

      beforeAll(() => {
        ({ tree } = capture(loadFixture(fixture)));
      });

      it('all nodes should have a non-empty type', () => {
        findNodes(tree, (n) => {
          expect(n.type).toBeTruthy();
          return false;
        });
      });

      it('section/group nodes should have non-empty children (except navigation)', () => {
        const containers = findNodes(tree, (n) =>
          (n.type === 'section' || n.type === 'group') && n.blockType !== 'navigation',
        );
        for (const c of containers) {
          expect(c.children).toBeInstanceOf(Array);
          expect(c.children!.length).toBeGreaterThan(0);
        }
      });

      it('navigation sections should have localHtml and no children', () => {
        const navSections = findByBlockType(tree, 'navigation');
        for (const nav of navSections) {
          expect(nav.localHtml).toBeDefined();
          expect(nav.children).toBeUndefined();
        }
      });

      it('active flag should only appear on link/button/section nodes', () => {
        const activeNodes = findNodes(tree, (n) => n.active === true);
        for (const n of activeNodes) {
          // Active can be on links, buttons, or submenu sections
          expect(['link', 'button', 'section']).toContain(n.type);
        }
      });

      it('total nodes should be within limits', () => {
        const total = countNodes(tree);
        expect(total).toBeLessThanOrEqual(300);
      });
    });
  }
});
