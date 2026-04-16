import { beforeEach, describe, expect, it } from 'vitest';

import type { StateNode } from '@web-agent-flow/shared-types';
import { captureInitialState } from '../recorder/initial-state';

function findNodes(nodes: StateNode[], predicate: (node: StateNode) => boolean): StateNode[] {
  const found: StateNode[] = [];
  const walk = (list: StateNode[]) => {
    for (const node of list) {
      if (predicate(node)) found.push(node);
      if (node.children) walk(node.children);
    }
  };
  walk(nodes);
  return found;
}

describe('captureInitialState edge cases', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    document.title = 'Edge Cases';
  });

  it('captures navigation, page heading, primary actions, dialog, iframe, and generic fallbacks', () => {
    document.body.innerHTML = `
      <header>
        <nav aria-label="Main Nav">
          <a href="/overview">Overview</a>
          <a href="/active" class="active">Active</a>
        </nav>
      </header>
      <main>
        <h1>Control Center</h1>
        <button>保存</button>
        <button>取消</button>

        <div id="card" class="settings-card" data-name="card-1">
          <div class="card-header"><div class="card-title">Profile Card</div></div>
          <div class="card-body"><button>编辑</button></div>
        </div>

        <div role="dialog" aria-label="Danger Zone">
          <p>Danger content</p>
          <button>确认</button>
        </div>

        <iframe title="Preview Frame">
          <body>
            <div class="frame-panel">
              <button>Frame Action</button>
            </div>
          </body>
        </iframe>

        <div id="media-box"><img src="https://example.com/a.png" /></div>
        <div contenteditable="true" aria-label="Rich Notes">Editable note</div>
      </main>
    `;

    const result = captureInitialState();

    expect(result.pageHeading).toBe('Control Center');
    expect(result.primaryActions).toEqual(expect.arrayContaining(['保存', '取消', '编辑', '确认']));
    expect(result.pageUrl).toBe(window.location.href);
    expect(result.rawHtmlSnapshot).toBeTruthy();

    const nav = findNodes(result.stateTree ?? [], (node) => node.blockType === 'navigation')[0];
    expect(nav?.label).toBe('Header');
    expect(nav?.summaryText).toContain('Active');
    expect(nav?.localHtml).toContain('/active');

    const dialog = findNodes(result.stateTree ?? [], (node) => node.blockType === 'dialog')[0];
    expect(dialog?.label).toBe('Danger Zone');

    const iframe = findNodes(result.stateTree ?? [], (node) => node.blockType === 'iframe-content')[0];
    expect(iframe?.label).toBe('Preview Frame');
    expect(findNodes(iframe?.children ?? [], (node) => node.label === 'Frame Action')).toHaveLength(1);

    const richtext = findNodes(result.stateTree ?? [], (node) => node.type === 'richtext')[0];
    expect(richtext?.label).toBe('Rich Notes');
    expect(richtext?.value).toBe('Editable note');

    const mediaFallback = findNodes(result.stateTree ?? [], (node) => node.selector?.includes('#media-box'))[0];
    expect(mediaFallback?.type).toBe('custom');
    expect(mediaFallback?.localHtml).toContain('<img');

    const card = findNodes(result.stateTree ?? [], (node) => node.label === 'Profile Card')[0];
    expect(card?.type).toBeTruthy();
    expect(card?.localHtml ?? '').toContain('编辑');
  });

  it('expands multi-control form items but ignores hidden popup controls', () => {
    document.body.innerHTML = `
      <main>
        <div class="el-form-item" prop="address">
          <label class="el-form-item__label">Address</label>
          <div class="el-form-item__content">
            <input name="street" value="Main St" />
            <input name="zip" value="10001" />
            <select><option selected>Shanghai</option></select>
            <div style="display:none">
              <button>Should Stay Hidden</button>
            </div>
          </div>
        </div>
      </main>
    `;

    const result = captureInitialState();
    const address = findNodes(result.stateTree ?? [], (node) => node.label === 'Address')[0];

    expect(address?.type).toBe('group');
    expect(address?.fieldProp).toBe('address');
    const values = findNodes(address?.children ?? [], (node) => !!node.value).map((node) => node.value);
    expect(values).toContain('Shanghai');
    const hiddenButtons = findNodes(address?.children ?? [], (node) => node.label === 'Should Stay Hidden');
    expect(hiddenButtons).toHaveLength(1);
    expect(hiddenButtons[0]?.cssState).toBe('display:none');
  });

  it('keeps repeated siblings as separate content instead of collapsing them away', () => {
    document.body.innerHTML = `
      <main>
        <section>
          <div class="task-card"><h2>Task A</h2><button>Run A</button></div>
          <div class="task-card"><h2>Task B</h2><button>Run B</button></div>
          <div class="task-card"><h2>Task C</h2><button>Run C</button></div>
          <div class="task-card"><h2>Task D</h2><button>Run D</button></div>
        </section>
      </main>
    `;

    const result = captureInitialState();
    const labels = findNodes(result.stateTree ?? [], (node) => node.type === 'button').map((node) => node.label);
    expect(labels).toEqual(expect.arrayContaining(['Run A', 'Run B', 'Run C', 'Run D']));
    expect(findNodes(result.stateTree ?? [], (node) => node.label?.includes('其他'))).toHaveLength(0);
  });
});
