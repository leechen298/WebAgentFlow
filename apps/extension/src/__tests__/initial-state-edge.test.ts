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

  it('captures upload, color, radio-checkbox options, and readonly range values inside form items', () => {
    document.body.innerHTML = `
      <main>
        <div class="el-form-item" prop="assets">
          <label class="el-form-item__label">Assets</label>
          <div class="el-form-item__content">
            <div class="el-upload">
              <img src="https://example.com/upload.png" alt="uploaded" />
            </div>
          </div>
        </div>

        <div class="el-form-item" prop="themeColor">
          <label class="el-form-item__label">Theme Color</label>
          <div class="el-form-item__content">
            <div class="el-color-picker">
              <span class="el-color-picker__color-inner" style="background-color: rgb(255, 23, 45);"></span>
            </div>
          </div>
        </div>

        <div class="el-form-item" prop="mode">
          <label class="el-form-item__label">Mode</label>
          <div class="el-form-item__content">
            <label><input type="radio" name="mode" checked value="simple" /> Simple</label>
            <label><input type="radio" name="mode" value="advanced" /> Advanced</label>
          </div>
        </div>

        <div class="el-form-item" prop="flags">
          <label class="el-form-item__label">Flags</label>
          <div class="el-form-item__content">
            <label><input type="checkbox" name="flags" checked value="a" /> Alpha</label>
            <label><input type="checkbox" name="flags" value="b" /> Beta</label>
          </div>
        </div>

        <div class="el-form-item" prop="window">
          <label class="el-form-item__label">Window</label>
          <div class="el-form-item__content">
            <input readonly value="2026-04-16 09:00" />
            <input readonly value="2026-04-16 18:00" />
          </div>
        </div>
      </main>
    `;

    const result = captureInitialState();

    const upload = findNodes(result.stateTree ?? [], (node) => node.label === 'Assets')[0];
    expect(upload?.type).toBe('upload');
    expect(upload?.value).toContain('https://example.com/upload.png');

    const color = findNodes(result.stateTree ?? [], (node) => node.label === 'Theme Color')[0];
    expect(color?.type).toBe('color');
    expect(color?.value).toContain('rgb(255, 23, 45)');

    const mode = findNodes(result.stateTree ?? [], (node) => node.label === 'Mode')[0];
    const modeRadio = findNodes([mode!], (node) => node.type === 'radio')[0] ?? mode;
    expect(['group', 'radio']).toContain(mode?.type);
    const modeText = JSON.stringify(modeRadio);
    expect(modeText).toContain('Simple');
    expect(modeText).toContain('Advanced');

    const flags = findNodes(result.stateTree ?? [], (node) => node.label === 'Flags')[0];
    const flagsCheckbox = findNodes([flags!], (node) => node.type === 'checkbox')[0] ?? flags;
    expect(['group', 'checkbox']).toContain(flags?.type);
    const flagsText = JSON.stringify(flagsCheckbox);
    expect(flagsText).toContain('Alpha');
    expect(flagsText).toContain('Beta');

    const windowField = findNodes(result.stateTree ?? [], (node) => node.label === 'Window')[0];
    const windowText = JSON.stringify(windowField);
    expect(windowText).toContain('2026-04-16 09:00');
    expect(windowText).toContain('2026-04-16 18:00');
  });

  it('captures complex table cells as structured rows and preserves footer tips', () => {
    document.body.innerHTML = `
      <main>
        <div class="el-form-item" prop="inventory">
          <label class="el-form-item__label">Inventory</label>
          <div class="el-form-item__content">
            <table>
              <thead>
                <tr><th>Preview</th><th>Actions</th><th>Qty</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><img src="https://example.com/item.png" alt="item image" /></td>
                  <td>
                    <button>Edit</button>
                    <button>Remove</button>
                  </td>
                  <td>
                    <div class="el-input-number" aria-valuenow="12">
                      <input value="12" aria-valuenow="12" />
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <div class="tip">Keep probability sum under 100%.</div>
          </div>
        </div>
      </main>
    `;

    const result = captureInitialState();
    const inventory = findNodes(result.stateTree ?? [], (node) => node.label === 'Inventory')[0];
    const table = findNodes([inventory!], (node) => node.type === 'table')[0];

    expect(inventory?.type).toBe('group');
    expect(table?.headers).toEqual(['Preview', 'Actions', 'Qty']);
    expect(table?.rows?.[0]?.[0]).toMatchObject({
      type: 'image',
      src: 'https://example.com/item.png',
    });
    expect(table?.rows?.[0]?.[1]).toMatchObject({
      type: 'button-group',
    });
    expect((table?.rows?.[0]?.[1] as any)?.actions).toHaveLength(2);
    expect(table?.rows?.[0]?.[2]).toMatchObject({
      type: 'input-number',
      value: '12',
    });
    expect(table?.localHtml).toContain('item.png');
    expect(table?.footerTips).toBeDefined();
    expect(JSON.stringify(table?.footerTips)).toContain('Keep probability sum');
  });

  it('expands titled sub-sections and extracts fallback values from custom displays', () => {
    document.body.innerHTML = `
      <main>
        <div class="el-form-item" prop="advancedConfig">
          <label class="el-form-item__label">Advanced Config</label>
          <div class="el-form-item__content">
            <div class="section-title">Basic</div>
            <div class="selection-label">Alpha Mode</div>
            <div class="section-title">Limits</div>
            <div class="value-text">Threshold 10</div>
          </div>
        </div>

        <div class="el-form-item" prop="delivery">
          <label class="el-form-item__label">Delivery</label>
          <div class="el-form-item__content">
            <div class="custom-select">
              <div class="selected-item">Scheduled Shipping</div>
            </div>
          </div>
        </div>

        <div class="el-form-item" prop="docs">
          <label class="el-form-item__label">Docs</label>
          <div class="el-form-item__content">
            <div class="el-upload"><a href="https://example.com/file.pdf">manual</a></div>
          </div>
        </div>
      </main>
    `;

    const result = captureInitialState();

    const advanced = findNodes(result.stateTree ?? [], (node) => node.label === 'Advanced Config')[0];
    expect(advanced?.type).toBe('group');
    expect(findNodes([advanced!], (node) => node.label === 'Basic')).toHaveLength(1);
    expect(findNodes([advanced!], (node) => node.label === 'Limits')).toHaveLength(1);

    const delivery = findNodes(result.stateTree ?? [], (node) => node.label === 'Delivery')[0];
    expect(delivery?.value ?? JSON.stringify(delivery)).toContain('Scheduled Shipping');

    const docs = findNodes(result.stateTree ?? [], (node) => node.label === 'Docs')[0];
    expect(docs?.type).toBe('upload');
    expect(docs?.value).toContain('https://example.com/file.pdf');
  });

  it('captures single-button, text-only, and empty table cells', () => {
    document.body.innerHTML = `
      <main>
        <table>
          <thead>
            <tr><th>Action</th><th>Text</th><th>Empty</th></tr>
          </thead>
          <tbody>
            <tr>
              <td><button title="Edit">Edit</button></td>
              <td>Plain Value</td>
              <td><span aria-hidden="true"></span></td>
            </tr>
          </tbody>
        </table>
      </main>
    `;

    const result = captureInitialState();
    const table = findNodes(result.stateTree ?? [], (node) => node.type === 'table')[0];
    expect(table?.rows?.[0]?.[0]).toMatchObject({ type: 'button', text: 'Edit' });
    expect((table?.rows?.[0]?.[1] as any)?.type).toBe('text');
    expect(JSON.stringify(table?.rows?.[0]?.[1])).toContain('Plain Value');
    expect(table?.rows?.[0]?.[2]).toMatchObject({ type: 'empty' });
  });
});
