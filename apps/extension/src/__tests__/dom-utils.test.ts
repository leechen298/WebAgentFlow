import { beforeEach, describe, expect, it } from 'vitest';
import {
  buildFieldPath,
  cleanLabel,
  extractHeadingText,
  extractItemTitle,
  findSectionLabel,
  isVisible,
  normalizeText,
  summarizeElementText,
} from '../recorder/dom-utils';

describe('DOM utilities', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('normalizes labels and field paths', () => {
    expect(cleanLabel(' Name*: ')).toBe('Name');
    expect(normalizeText('foo   \n bar')).toBe('foo bar');
    expect(buildFieldPath('Account', 'Name', 'Account', 'Name')).toBe('Account / Name');
  });

  it('detects visibility from inline styles and size patches', () => {
    const visible = document.createElement('div');
    const hidden = document.createElement('div');
    hidden.style.display = 'none';
    document.body.append(visible, hidden);

    expect(isVisible(visible)).toBe(true);
    expect(isVisible(hidden)).toBe(false);
  });

  it('extracts heading text and section labels from nearby structure', () => {
    document.body.innerHTML = `
      <section>
        <h2>Billing Settings</h2>
        <div class="field"><input id="card" /></div>
      </section>
    `;
    const heading = document.querySelector('h2')!;
    const field = document.querySelector('.field')!;

    expect(extractHeadingText(heading)).toBe('Billing Settings');
    expect(findSectionLabel(field)).toBe('Billing Settings');
  });

  it('summarizes interactive values and item titles', () => {
    document.body.innerHTML = `
      <div id="wrapper">
        <input value="Alice" />
        <button>Remove</button>
      </div>
      <div class="card">
        <strong>Order 1001</strong>
        <p>Processing</p>
      </div>
    `;

    expect(summarizeElementText(document.getElementById('wrapper')!)).toBe('Alice');
    expect(extractItemTitle(document.querySelector('.card')!)).toBe('Order 1001');
  });

  it('falls back to image marker when only images remain', () => {
    document.body.innerHTML = '<div id="img-only"><img src="/x.png" /></div>';
    expect(summarizeElementText(document.getElementById('img-only')!)).toBe('[image]');
  });
});
