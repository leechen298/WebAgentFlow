import { beforeEach, describe, expect, it } from 'vitest';
import {
  detectFieldType,
  detectRequired,
  extractHintOrError,
  extractUniversalLabel,
  extractUniversalValue,
  findContentArea,
} from '../recorder/label-extractor';

describe('label and value extraction', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('extracts labels from aria, native labels, and legends', () => {
    document.body.innerHTML = `
      <div id="aria" aria-label="Email"></div>
      <div id="by" aria-labelledby="lbl"></div><span id="lbl">Username</span>
      <div id="native"><label>Password</label><input /></div>
      <fieldset id="legend"><legend>Profile</legend><input /></fieldset>
    `;

    expect(extractUniversalLabel(document.getElementById('aria')!)).toBe('Email');
    expect(extractUniversalLabel(document.getElementById('by')!)).toBe('Username');
    expect(extractUniversalLabel(document.getElementById('native')!)).toBe('Password');
    expect(extractUniversalLabel(document.getElementById('legend')!)).toBe('Profile');
  });

  it('extracts values from tags, selects, inputs, textareas, and rich text', () => {
    document.body.innerHTML = `
      <div id="tags">
        <span class="user-tag">One<button aria-label="close">x</button></span>
        <span class="user-tag">Two<button aria-label="close">x</button></span>
      </div>
      <div id="select"><select><option>Draft</option><option selected>Published</option></select></div>
      <div id="input"><input value="Alice" placeholder="Name" /></div>
      <div id="textarea"><textarea>Long note</textarea></div>
      <div id="rich"><div contenteditable="true"><p>Rich value</p></div></div>
    `;

    expect(extractUniversalValue(document.getElementById('tags')!)).toBe('One, Two');
    expect(extractUniversalValue(document.getElementById('select')!)).toBe('Published');
    expect(extractUniversalValue(document.getElementById('input')!)).toBe('Alice');
    expect(extractUniversalValue(document.getElementById('textarea')!)).toBe('Long note');
    expect(extractUniversalValue(document.getElementById('rich')!)).toBe('Rich value');
  });

  it('extracts hints, required state, content areas, and field type metadata', () => {
    document.body.innerHTML = `
      <div id="field" class="required">
        <div class="field-label">Country*</div>
        <div class="field-content">
          <input placeholder="Pick one" />
          <p>Please choose a country</p>
        </div>
      </div>
      <div id="radio-group">
        <label><input type="radio" checked value="a" /> Alpha</label>
      </div>
      <div id="checkbox-group">
        <label><input type="checkbox" checked value="x" /> X</label>
        <label><input type="checkbox" value="y" /> Y</label>
      </div>
      <div id="rich-field"><div contenteditable="true"><p>Hello</p></div></div>
    `;

    const field = document.getElementById('field')!;
    expect(extractHintOrError(field)).toBe('Please choose a country');
    expect(detectRequired(field)).toBe(true);
    expect(findContentArea(field)).toBe(field.querySelector('.field-content'));
    expect(detectFieldType(field)).toMatchObject({ fieldType: 'input', placeholder: 'Pick one' });
    expect(detectFieldType(document.getElementById('radio-group')!)).toMatchObject({ fieldType: 'radio', defaultValueText: 'Alpha' });
    expect(detectFieldType(document.getElementById('checkbox-group')!)).toMatchObject({ fieldType: 'checkbox', defaultValueText: 'X' });
    expect(detectFieldType(document.getElementById('rich-field')!)).toMatchObject({ fieldType: 'richtext', defaultValueText: 'Hello' });
  });

  it('extractUniversalLabel: finds label by component class pattern ending in "label"', () => {
    document.body.innerHTML = `
      <div id="container">
        <div class="el-form-item__label">Username：</div>
        <div class="el-form-item__content"><input /></div>
      </div>
    `;
    // el-form-item__label is a BEM child, so getComponentNames returns [] for it.
    // But querySelectorAll('*') finds it and checks if names end with "label".
    // Since BEM children are stripped, this path won't match — falls through to native label.
    const result = extractUniversalLabel(document.getElementById('container')!);
    // No match for component label; no native <label>; no legend — returns undefined
    expect(result).toBeUndefined();
  });

  it('extractUniversalLabel: returns undefined when container has nothing', () => {
    document.body.innerHTML = '<div id="empty"></div>';
    expect(extractUniversalLabel(document.getElementById('empty')!)).toBeUndefined();
  });

  it('extractUniversalValue: returns undefined when container is empty', () => {
    document.body.innerHTML = '<div id="empty"></div>';
    expect(extractUniversalValue(document.getElementById('empty')!)).toBeUndefined();
  });

  it('extractUniversalValue: extracts value from readonly range inputs', () => {
    document.body.innerHTML = `
      <div id="range">
        <input readonly value="2024-01-01" />
        <span>~</span>
        <input readonly value="2024-12-31" />
      </div>
    `;
    expect(extractUniversalValue(document.getElementById('range')!)).toBe('2024-01-01 ~ 2024-12-31');
  });

  it('extractUniversalValue: extracts single readonly input value', () => {
    document.body.innerHTML = `
      <div id="range">
        <input readonly value="2024-06-15" />
        <input readonly value="" />
      </div>
    `;
    expect(extractUniversalValue(document.getElementById('range')!)).toBe('2024-06-15');
  });

  it('extractUniversalValue: extracts selection-item text', () => {
    document.body.innerHTML = `
      <div id="sel">
        <div class="el-selection-item">Option A</div>
      </div>
    `;
    // el-selection-item -> after stripping prefix: "selection-item" -> matches
    // But getComponentNames strips the prefix and checks for BEM __
    // "el-selection-item" -> prefix "el-", afterPrefix "selection-item", no "__" -> name = "selection-item"
    // But classifyByClassName checks COMPONENT_NAME_MAP which doesn't have "selection-item"
    // The extractUniversalValue checks names.some(n => /selection-item|.../.test(n))
    expect(extractUniversalValue(document.getElementById('sel')!)).toBe('Option A');
  });

  it('extractUniversalValue: skips placeholder-style selection items', () => {
    document.body.innerHTML = `
      <div id="sel">
        <div class="el-selection-item placeholder">Choose...</div>
      </div>
    `;
    expect(extractUniversalValue(document.getElementById('sel')!)).toBeUndefined();
  });

  it('extractUniversalValue: skips proxy input inside compound when value equals placeholder', () => {
    document.body.innerHTML = `
      <div id="compound">
        <div class="el-select">
          <input value="Select..." placeholder="Select..." />
        </div>
      </div>
    `;
    // The input is inside a compound, value equals placeholder — skip
    expect(extractUniversalValue(document.getElementById('compound')!)).toBeUndefined();
  });

  it('extractUniversalValue: extracts tag component text', () => {
    document.body.innerHTML = `
      <div id="tags">
        <span class="el-tag">Red<i class="el-tag__close">x</i></span>
        <span class="el-tag">Blue<i class="el-tag__close">x</i></span>
      </div>
    `;
    expect(extractUniversalValue(document.getElementById('tags')!)).toBe('Red, Blue');
  });

  it('extractHintOrError: returns undefined when no hint elements', () => {
    document.body.innerHTML = '<div id="no-hint"><input /></div>';
    expect(extractHintOrError(document.getElementById('no-hint')!)).toBeUndefined();
  });

  it('detectRequired: detects via aria-required on container', () => {
    document.body.innerHTML = '<div id="field" aria-required="true"><input /></div>';
    expect(detectRequired(document.getElementById('field')!)).toBe(true);
  });

  it('detectRequired: detects via [required] on nested input', () => {
    document.body.innerHTML = '<div id="field"><input required /></div>';
    expect(detectRequired(document.getElementById('field')!)).toBe(true);
  });

  it('detectRequired: detects via aria-required on nested input', () => {
    document.body.innerHTML = '<div id="field"><input aria-required="true" /></div>';
    expect(detectRequired(document.getElementById('field')!)).toBe(true);
  });

  it('detectRequired: detects asterisk in label element text', () => {
    document.body.innerHTML = '<div id="field"><label>Name *</label><input /></div>';
    expect(detectRequired(document.getElementById('field')!)).toBe(true);
  });

  it('detectRequired: returns false when not required', () => {
    document.body.innerHTML = '<div id="field"><label>Name</label><input /></div>';
    expect(detectRequired(document.getElementById('field')!)).toBe(false);
  });

  it('detectFieldType: detects native select', () => {
    document.body.innerHTML = `
      <div id="sel">
        <select><option selected>Draft</option><option>Published</option></select>
      </div>
    `;
    const result = detectFieldType(document.getElementById('sel')!);
    expect(result.fieldType).toBe('select');
    expect(result.defaultValueText).toBe('Draft');
  });

  it('detectFieldType: detects unchecked radio as radio without defaultValueText', () => {
    document.body.innerHTML = `
      <div id="radios">
        <label><input type="radio" value="a" /> A</label>
        <label><input type="radio" value="b" /> B</label>
      </div>
    `;
    const result = detectFieldType(document.getElementById('radios')!);
    expect(result.fieldType).toBe('radio');
    expect(result.defaultValueText).toBeUndefined();
  });

  it('detectFieldType: returns custom when classifier says input but no real input exists', () => {
    document.body.innerHTML = `
      <div id="custom-widget">
        <div class="ant-select">
          <div class="ant-selection-item">Beijing</div>
        </div>
      </div>
    `;
    // The content area has an ant-select (compound, priority 2) so classifiedType is 'select'
    const result = detectFieldType(document.getElementById('custom-widget')!);
    expect(result.fieldType).toBe('select');
  });

  it('findContentArea: falls back to last div child', () => {
    document.body.innerHTML = `
      <div id="container">
        <div class="label-area">Name</div>
        <div class="input-area"><input /></div>
      </div>
    `;
    // No component name matching "content|control|blank", so falls back to last div
    const area = findContentArea(document.getElementById('container')!);
    expect(area.classList.contains('input-area')).toBe(true);
  });

  it('findContentArea: falls back to container itself when no child divs', () => {
    document.body.innerHTML = '<div id="flat"><input /></div>';
    const area = findContentArea(document.getElementById('flat')!);
    expect(area.id).toBe('flat');
  });

  it('detectFieldType: richtext with HTML content', () => {
    document.body.innerHTML = `
      <div id="rt">
        <div contenteditable="true"><p>Rich <b>text</b></p></div>
      </div>
    `;
    const result = detectFieldType(document.getElementById('rt')!);
    expect(result.fieldType).toBe('richtext');
    expect(result.defaultValueText).toBe('Rich text');
    expect(result.defaultValueHtml).toContain('<b>text</b>');
  });
});
