import { beforeEach, describe, expect, it } from 'vitest';
import { getSimpleSelector, getTargetInfo } from '../recorder/events';

describe('event helper utilities', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('builds a simple selector from id, tag, classes, and name', () => {
    document.body.innerHTML = '<input id="email" class="primary rounded extra" name="user-email" />';
    const el = document.querySelector('input')!;

    expect(getSimpleSelector(el)).toBe('#emailinput.primary.rounded[name="user-email"]');
  });

  it('extracts label from aria-label and related metadata', () => {
    document.body.innerHTML = '<button id="save" aria-label="Save item" class="cta primary" role="button" title="Save this">Save</button>';
    const el = document.querySelector('button')!;

    expect(getTargetInfo(el)).toMatchObject({
      tag: 'button',
      id: 'save',
      text: 'Save',
      label: 'Save item',
      className: 'cta primary',
      role: 'button',
      nearbyText: 'Save this',
    });
  });

  it('resolves labels from associated labels and wrapping label text', () => {
    document.body.innerHTML = `
      <label for="username">Username</label>
      <input id="username" placeholder="Enter user" />
      <label>Wrapped text<input id="wrapped" /></label>
    `;

    const input = document.getElementById('username') as HTMLInputElement;
    const wrapped = document.getElementById('wrapped') as HTMLInputElement;

    expect(getTargetInfo(input)).toMatchObject({
      tag: 'input',
      label: 'Username',
      placeholder: 'Enter user',
    });
    expect(getTargetInfo(wrapped).nearbyText).toBe('Wrapped text');
  });

  it('uses aria-labelledby and previous sibling text as nearby text fallbacks', () => {
    document.body.innerHTML = `
      <span id="desc">Search docs</span>
      <input id="search" aria-labelledby="desc" />
      <span class="field-label">Phone</span>
      <input id="phone" />
    `;

    const search = document.getElementById('search')!;
    const phone = document.getElementById('phone')!;

    expect(getTargetInfo(search).nearbyText).toBe('Search docs');
    expect(getTargetInfo(phone).nearbyText).toBe('Phone');
  });
});
