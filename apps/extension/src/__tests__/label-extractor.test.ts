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
});
