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
});
