import { describe, expect, it } from 'vitest';

import {
  classifyContainerContent,
  classifyElement,
  findFormContainer,
  getComponentNames,
  isBoundaryElement,
  isFormContainer,
  isInsideCompound,
  isNavigationChrome,
} from '../recorder/component-classifier';

describe('component-classifier', () => {
  it('classifies elements by aria, class, structure, and native html', () => {
    const aria = document.createElement('div');
    aria.setAttribute('role', 'combobox');
    expect(classifyElement(aria)).toEqual({ type: 'select', source: 'aria' });

    const byClass = document.createElement('div');
    byClass.className = 'el-select';
    expect(classifyElement(byClass)).toEqual({ type: 'select', source: 'class' });

    const richtextWrap = document.createElement('div');
    richtextWrap.innerHTML = `
      <div class="toolbar"></div>
      <div contenteditable="true">hello</div>
    `;
    const richtext = richtextWrap.querySelector('[contenteditable="true"]') as Element;
    expect(classifyElement(richtext)).toEqual({ type: 'richtext', source: 'structure' });

    const native = document.createElement('input');
    native.type = 'date';
    expect(classifyElement(native)).toEqual({ type: 'date', source: 'native' });
  });

  it('detects more native and structural component variants', () => {
    const monaco = document.createElement('div');
    monaco.className = 'monaco-editor';
    expect(classifyElement(monaco)).toEqual({ type: 'code-editor', source: 'structure' });

    const input = document.createElement('input');
    input.type = 'range';
    expect(classifyElement(input)?.type).toBe('slider');

    const file = document.createElement('input');
    file.type = 'file';
    expect(classifyElement(file)?.type).toBe('upload');

    const progress = document.createElement('progress');
    expect(classifyElement(progress)?.type).toBe('progress');

    const nav = document.createElement('nav');
    expect(classifyElement(nav)?.type).toBe('navigation');
  });

  it('extracts class component names without treating BEM child classes as parents', () => {
    const child = document.createElement('div');
    child.className = 'el-form-item__label data-darkreader';
    expect(getComponentNames(child)).toEqual([]);
    expect(classifyElement(child)).toBeUndefined();
  });

  it('detects form containers and navigation chrome', () => {
    const fieldset = document.createElement('fieldset');
    expect(isFormContainer(fieldset)).toBe(true);

    const header = document.createElement('header');
    expect(isNavigationChrome(header)).toBe(true);

    const menu = document.createElement('div');
    menu.className = 'ant-menu';
    expect(isNavigationChrome(menu)).toBe(true);
  });

  it('prefers higher priority compound controls inside containers', () => {
    const area = document.createElement('div');
    area.innerHTML = `
      <div class="el-input">
        <input type="text" />
      </div>
      <div class="el-select">
        <input type="text" />
      </div>
    `;

    expect(classifyContainerContent(area)).toBe('select');
  });

  it('detects when an element is inside a compound component', () => {
    const direct = document.createElement('input');
    direct.setAttribute('aria-haspopup', 'true');
    expect(isInsideCompound(direct)).toBe(true);

    const host = document.createElement('div');
    host.innerHTML = `
      <div class="el-select">
        <div class="el-input">
          <input id="nested-input" />
        </div>
      </div>
    `;
    document.body.appendChild(host);
    const nested = host.querySelector('#nested-input') as Element;
    expect(isInsideCompound(nested)).toBe(true);

    const plain = document.createElement('input');
    host.appendChild(plain);
    expect(isInsideCompound(plain)).toBe(false);

    host.remove();
  });

  it('finds form containers and respects traversal boundaries', () => {
    const host = document.createElement('div');
    host.innerHTML = `
      <form>
        <div class="el-form-item" id="field">
          <div class="el-input"><input id="field-input" /></div>
        </div>
      </form>
      <div role="dialog" id="dialog">
        <div class="el-form-item" id="dialog-field">
          <input id="dialog-input" />
        </div>
      </div>
      <div role="main" id="main">
        <div><input id="main-input" /></div>
      </div>
      <table id="table"><tr><td><input id="table-input" /></td></tr></table>
    `;
    document.body.appendChild(host);

    expect(findFormContainer(host.querySelector('#field-input') as Element)?.id).toBe('field');
    expect(findFormContainer(host.querySelector('#dialog-input') as Element)?.id).toBe('dialog-field');
    expect(findFormContainer(host.querySelector('#main-input') as Element)).toBeUndefined();
    expect(findFormContainer(host.querySelector('#table-input') as Element)).toBeUndefined();

    expect(isBoundaryElement(host.querySelector('#dialog') as Element)).toBe(true);
    expect(isBoundaryElement(host.querySelector('#table') as Element)).toBe(true);
    expect(isBoundaryElement(host.querySelector('#main') as Element)).toBe(true);

    host.remove();
  });
});
