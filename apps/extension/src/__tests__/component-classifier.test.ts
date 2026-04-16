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

  it('classifies MUI-style camelCase classes', () => {
    const el = document.createElement('div');
    el.className = 'MuiSelect-root other-class';
    expect(classifyElement(el)).toEqual({ type: 'select', source: 'class' });
  });

  it('classifies various native input types', () => {
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    expect(classifyElement(checkbox)).toEqual({ type: 'checkbox', source: 'native' });

    const radio = document.createElement('input');
    radio.type = 'radio';
    expect(classifyElement(radio)).toEqual({ type: 'radio', source: 'native' });

    const number = document.createElement('input');
    number.type = 'number';
    expect(classifyElement(number)).toEqual({ type: 'number', source: 'native' });

    const color = document.createElement('input');
    color.type = 'color';
    expect(classifyElement(color)).toEqual({ type: 'color', source: 'native' });

    const time = document.createElement('input');
    time.type = 'time';
    expect(classifyElement(time)).toEqual({ type: 'time', source: 'native' });

    const textarea = document.createElement('textarea');
    expect(classifyElement(textarea)).toEqual({ type: 'textarea', source: 'native' });

    const select = document.createElement('select');
    expect(classifyElement(select)).toEqual({ type: 'select', source: 'native' });

    const dialog = document.createElement('dialog');
    expect(classifyElement(dialog)).toEqual({ type: 'dialog', source: 'native' });

    const meter = document.createElement('meter');
    expect(classifyElement(meter)).toEqual({ type: 'progress', source: 'native' });

    const fieldset = document.createElement('fieldset');
    expect(classifyElement(fieldset)).toEqual({ type: 'form-item', source: 'native' });
  });

  it('classifies structural editors', () => {
    const prose = document.createElement('div');
    prose.setAttribute('contenteditable', 'true');
    prose.className = 'ProseMirror';
    expect(classifyElement(prose)).toEqual({ type: 'richtext', source: 'structure' });

    const ql = document.createElement('div');
    ql.setAttribute('contenteditable', 'true');
    ql.className = 'ql-editor';
    expect(classifyElement(ql)).toEqual({ type: 'richtext', source: 'structure' });

    const ck = document.createElement('div');
    ck.setAttribute('contenteditable', 'true');
    ck.className = 'ck-content';
    expect(classifyElement(ck)).toEqual({ type: 'richtext', source: 'structure' });

    const slate = document.createElement('div');
    slate.setAttribute('contenteditable', 'true');
    slate.setAttribute('data-slate-editor', 'true');
    expect(classifyElement(slate)).toEqual({ type: 'richtext', source: 'structure' });

    // wangEditor
    const wangContainer = document.createElement('div');
    wangContainer.className = 'w-e-text-container';
    const wangEditor = document.createElement('div');
    wangEditor.setAttribute('contenteditable', 'true');
    wangContainer.appendChild(wangEditor);
    document.body.appendChild(wangContainer);
    expect(classifyElement(wangEditor)).toEqual({ type: 'richtext', source: 'structure' });
    wangContainer.remove();

    // TinyMCE wrapper
    const tox = document.createElement('div');
    tox.className = 'tox-tinymce';
    expect(classifyElement(tox)).toEqual({ type: 'richtext', source: 'structure' });

    // CodeMirror
    const cm = document.createElement('div');
    cm.className = 'CodeMirror';
    expect(classifyElement(cm)).toEqual({ type: 'code-editor', source: 'structure' });

    const cmEditor = document.createElement('div');
    cmEditor.className = 'cm-editor';
    expect(classifyElement(cmEditor)).toEqual({ type: 'code-editor', source: 'structure' });
  });

  it('classifies code editor by data-mode-id child', () => {
    const el = document.createElement('div');
    el.innerHTML = '<div data-mode-id="javascript"></div>';
    expect(classifyElement(el)).toEqual({ type: 'code-editor', source: 'structure' });
  });

  it('classifies ARIA roles correctly', () => {
    const roles: Record<string, string> = {
      textbox: 'input',
      spinbutton: 'number',
      listbox: 'select',
      radiogroup: 'radio',
      switch: 'switch',
      slider: 'slider',
      progressbar: 'progress',
      tablist: 'tabs',
      tree: 'tree',
      alertdialog: 'dialog',
      menubar: 'menu',
      navigation: 'navigation',
      grid: 'table',
      separator: 'layout',
      tooltip: 'skip',
    };

    for (const [role, expectedType] of Object.entries(roles)) {
      const el = document.createElement('div');
      el.setAttribute('role', role);
      const result = classifyElement(el);
      expect(result).toBeDefined();
      expect(result!.type).toBe(expectedType);
      expect(result!.source).toBe('aria');
    }
  });

  it('classifies various library class prefixes', () => {
    const prefixTests: Array<[string, string]> = [
      ['ant-cascader', 'cascader'],
      ['n-date-picker', 'date'],
      ['arco-upload', 'upload'],
      ['van-stepper', 'number'],
      ['t-transfer', 'transfer'],
      ['semi-autocomplete', 'autocomplete'],
      ['ivu-color-picker', 'color'],
      ['p-dialog', 'dialog'],
      ['v-navigation-drawer', 'navigation'],
    ];

    for (const [cls, expectedType] of prefixTests) {
      const el = document.createElement('div');
      el.className = cls;
      const result = classifyElement(el);
      expect(result).toBeDefined();
      expect(result!.type).toBe(expectedType);
      expect(result!.source).toBe('class');
    }
  });

  it('strips BEM modifiers from class names', () => {
    const el = document.createElement('div');
    el.className = 'el-select--large';
    expect(classifyElement(el)).toEqual({ type: 'select', source: 'class' });
  });

  it('isInsideCompound detects listbox sibling', () => {
    const host = document.createElement('div');
    host.innerHTML = `
      <div id="wrapper">
        <div id="trigger"><input id="target" /></div>
        <div role="listbox"><div>Option A</div></div>
      </div>
    `;
    document.body.appendChild(host);
    const target = host.querySelector('#target') as Element;
    expect(isInsideCompound(target)).toBe(true);
    host.remove();
  });

  it('isInsideCompound returns true for aria-haspopup="listbox"', () => {
    const el = document.createElement('input');
    el.setAttribute('aria-haspopup', 'listbox');
    expect(isInsideCompound(el)).toBe(true);
  });

  it('isInsideCompound stops at form boundary', () => {
    const host = document.createElement('div');
    host.innerHTML = `
      <div class="el-select">
        <form>
          <input id="inside-form" />
        </form>
      </div>
    `;
    document.body.appendChild(host);
    // The form tag is a boundary, so el-select should not be reached
    const input = host.querySelector('#inside-form') as Element;
    expect(isInsideCompound(input)).toBe(false);
    host.remove();
  });

  it('isNavigationChrome detects footer, aside elements', () => {
    const footer = document.createElement('footer');
    expect(isNavigationChrome(footer)).toBe(true);

    const aside = document.createElement('aside');
    expect(isNavigationChrome(aside)).toBe(true);
  });

  it('isNavigationChrome returns false for unclassifiable elements', () => {
    const div = document.createElement('div');
    expect(isNavigationChrome(div)).toBe(false);
  });

  it('classifyContainerContent returns input as default when no controls found', () => {
    const area = document.createElement('div');
    area.innerHTML = '<span>just text</span>';
    expect(classifyContainerContent(area)).toBe('input');
  });

  it('isBoundaryElement detects form and body', () => {
    const form = document.createElement('form');
    expect(isBoundaryElement(form)).toBe(true);
    expect(isBoundaryElement(document.body)).toBe(true);
  });

  it('classifyElement returns undefined for unclassifiable elements', () => {
    const div = document.createElement('div');
    expect(classifyElement(div)).toBeUndefined();
  });

  it('getComponentNames handles element with no class attribute', () => {
    const el = document.createElement('div');
    expect(getComponentNames(el)).toEqual([]);
  });

  it('hasToolbarSibling checks up to 3 levels for toolbar sibling', () => {
    const host = document.createElement('div');
    host.innerHTML = `
      <div class="editor-wrapper">
        <div role="toolbar">Bold Italic</div>
        <div class="content-wrapper">
          <div contenteditable="true" id="deep-editor">text</div>
        </div>
      </div>
    `;
    document.body.appendChild(host);
    const editor = host.querySelector('#deep-editor') as Element;
    expect(classifyElement(editor)).toEqual({ type: 'richtext', source: 'structure' });
    host.remove();
  });
});
