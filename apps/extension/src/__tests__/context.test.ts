import { beforeEach, describe, expect, it } from 'vitest';
import { getFieldContext } from '../recorder/context';

describe('field context extraction', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('extracts form-item context including label, path, value, required, and hint', () => {
    document.body.innerHTML = `
      <section>
        <h3>Profile</h3>
        <div class="el-form-item required" prop="email">
          <label>Email*</label>
          <div class="el-form-item__content">
            <input id="email" value="alice@example.com" />
            <p>Use your work email</p>
          </div>
        </div>
      </section>
    `;

    expect(getFieldContext(document.getElementById('email')!)).toMatchObject({
      containerType: 'form-item',
      fieldLabel: 'Email',
      sectionLabel: 'Profile',
      fieldPath: 'Profile / Email',
      fieldProp: 'email',
      fieldRequired: true,
      fieldValueText: 'alice@example.com',
      fieldHintText: 'Use your work email',
    });
  });

  it('extracts table-row context and skips action columns', () => {
    document.body.innerHTML = `
      <div class="table-title">Orders</div>
      <div>
        <table>
          <thead><tr><th>Item</th><th>Qty</th><th>操作</th></tr></thead>
          <tbody>
            <tr>
              <td><button id="cell-btn">Apple</button></td>
              <td>2</td>
              <td><button>Delete</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    `;

    expect(getFieldContext(document.getElementById('cell-btn')!)).toMatchObject({
      containerType: 'table-row',
      sectionLabel: 'Orders',
    });
  });

  it('extracts repeated list item context and returns undefined for unrelated nodes', () => {
    document.body.innerHTML = `
      <section>
        <h3>Tasks</h3>
        <div class="item"><strong>Task A</strong><button id="a">Run</button></div>
        <div class="item"><strong>Task B</strong><button id="b">Run</button></div>
      </section>
      <div id="outside">plain</div>
    `;

    expect(getFieldContext(document.getElementById('a')!)).toMatchObject({
      containerType: 'list-item',
      itemLabel: 'Task A',
      sectionLabel: 'Tasks',
    });
    expect(getFieldContext(document.getElementById('outside')!)).toBeUndefined();
  });

  it('returns table-row context with split-table header detection', () => {
    document.body.innerHTML = `
      <div class="my-table">
        <div class="header-wrapper">
          <table><thead><tr><th>Name</th><th>Age</th></tr></thead></table>
        </div>
        <table>
          <tbody>
            <tr>
              <td>Alice</td>
              <td><button id="age-btn">25</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
    const ctx = getFieldContext(document.getElementById('age-btn')!);
    expect(ctx).toBeDefined();
    expect(ctx?.containerType).toBe('table-row');
    expect(ctx?.fieldValueText).toContain('Alice');
  });

  it('returns table-row context with caption as label', () => {
    document.body.innerHTML = `
      <table>
        <caption>Products</caption>
        <thead><tr><th>Name</th><th>Price</th></tr></thead>
        <tbody>
          <tr>
            <td>Widget</td>
            <td><span id="price">10</span></td>
          </tr>
        </tbody>
      </table>
    `;
    const ctx = getFieldContext(document.getElementById('price')!);
    expect(ctx).toBeDefined();
    expect(ctx?.containerType).toBe('table-row');
    expect(ctx?.fieldLabel).toBe('Products');
  });

  it('returns form-item context without label or path when none found', () => {
    document.body.innerHTML = `
      <div class="el-form-item">
        <div class="el-form-item__content">
          <input id="bare-input" value="test" />
        </div>
      </div>
    `;
    const ctx = getFieldContext(document.getElementById('bare-input')!);
    expect(ctx).toBeDefined();
    expect(ctx?.containerType).toBe('form-item');
    expect(ctx?.fieldValueText).toBe('test');
  });

  it('list-item context skips tab/menu classified items', () => {
    document.body.innerHTML = `
      <div>
        <div class="el-tabs" role="tablist">
          <div class="tab" role="tab"><button id="tab-btn">Tab 1</button></div>
          <div class="tab" role="tab"><button>Tab 2</button></div>
        </div>
      </div>
    `;
    // tabs are menu/tabs-type items, should be skipped for list-item context
    const ctx = getFieldContext(document.getElementById('tab-btn')!);
    // Should not match as list-item because tabs are skipped
    expect(ctx?.containerType).not.toBe('list-item');
  });

  it('list-item returns undefined when no itemLabel and no value', () => {
    document.body.innerHTML = `
      <div>
        <div class="item"><div id="inner"></div></div>
        <div class="item"><div></div></div>
      </div>
    `;
    const ctx = getFieldContext(document.getElementById('inner')!);
    // items are empty — no title, no value
    expect(ctx).toBeUndefined();
  });

  it('getFieldContext swallows exceptions and returns undefined', () => {
    // Create a scenario where an internal call might throw
    // The try-catch in getFieldContext should handle it gracefully
    const el = document.createElement('div');
    // Not attached to document — some DOM operations may behave oddly
    expect(getFieldContext(el)).toBeUndefined();
  });

  it('table row context handles rows with no cells gracefully', () => {
    document.body.innerHTML = `
      <table>
        <thead><tr><th>H</th></tr></thead>
        <tbody><tr id="empty-row"></tr></tbody>
      </table>
    `;
    // Element is in a table row with no cells
    const row = document.getElementById('empty-row')!;
    const el = document.createElement('span');
    row.appendChild(el);
    // getTableRowContext checks cells.length === 0 and returns undefined
    const ctx = getFieldContext(el);
    expect(ctx).toBeUndefined();
  });
});
