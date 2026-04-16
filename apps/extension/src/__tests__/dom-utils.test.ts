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

  it('extractHeadingText returns undefined for long text', () => {
    const el = document.createElement('div');
    el.textContent = 'This is a very long text that exceeds the forty character limit for heading detection purposes';
    document.body.appendChild(el);
    // Text > 40 chars, so direct text won't match; inner heading also won't match
    expect(extractHeadingText(el)).toBeUndefined();
  });

  it('extractHeadingText returns undefined for very short text', () => {
    const el = document.createElement('div');
    el.textContent = 'X'; // < 2 chars
    document.body.appendChild(el);
    expect(extractHeadingText(el)).toBeUndefined();
  });

  it('extractHeadingText returns undefined for text ending with punctuation', () => {
    const el = document.createElement('div');
    el.textContent = 'Hello World；';
    document.body.appendChild(el);
    expect(extractHeadingText(el)).toBeUndefined();
  });

  it('extractHeadingText falls back to inner heading elements', () => {
    const el = document.createElement('div');
    el.innerHTML = '<span>long text that is definitely more than forty characters for the outer container test blah blah</span><strong>Section A</strong>';
    document.body.appendChild(el);
    expect(extractHeadingText(el)).toBe('Section A');
  });

  it('extractHeadingText inner heading skips long inner text', () => {
    const el = document.createElement('div');
    el.innerHTML = '<span>long outer text definitely over forty characters for this test</span><h2>This inner heading text is also very long and exceeds the limit</h2>';
    document.body.appendChild(el);
    expect(extractHeadingText(el)).toBeUndefined();
  });

  it('findSectionLabel excludes specified labels', () => {
    document.body.innerHTML = `
      <section>
        <h2>Settings</h2>
        <div id="target"><input /></div>
      </section>
    `;
    const field = document.querySelector('#target')!;
    expect(findSectionLabel(field, ['Settings'])).toBeUndefined();
  });

  it('findSectionLabel searches parent children for headings', () => {
    document.body.innerHTML = `
      <div>
        <h3>Overview</h3>
        <div><div><div id="deep">This text is too long to be considered a heading because it exceeds the forty character limit</div></div></div>
      </div>
    `;
    const deep = document.querySelector('#deep')!;
    expect(findSectionLabel(deep)).toBe('Overview');
  });

  it('findSectionLabel returns undefined when nothing found within depth', () => {
    document.body.innerHTML = '<div id="lonely"><input /></div>';
    expect(findSectionLabel(document.getElementById('lonely')!)).toBeUndefined();
  });

  it('isVisible returns true for body element', () => {
    expect(isVisible(document.body)).toBe(true);
  });

  it('isVisible detects visibility:hidden', () => {
    const el = document.createElement('div');
    el.style.visibility = 'hidden';
    document.body.appendChild(el);
    expect(isVisible(el)).toBe(false);
  });

  it('buildFieldPath returns undefined for all empty parts', () => {
    expect(buildFieldPath(undefined, '', undefined)).toBeUndefined();
  });

  it('summarizeElementText extracts select value', () => {
    document.body.innerHTML = `
      <div id="sel-wrap">
        <select><option>Alpha</option><option selected>Beta</option></select>
      </div>
    `;
    expect(summarizeElementText(document.getElementById('sel-wrap')!)).toBe('Beta');
  });

  it('summarizeElementText extracts textarea value', () => {
    document.body.innerHTML = `
      <div id="ta-wrap"><textarea>Some note</textarea></div>
    `;
    expect(summarizeElementText(document.getElementById('ta-wrap')!)).toBe('Some note');
  });

  it('summarizeElementText extracts input aria-valuenow when no value', () => {
    document.body.innerHTML = `
      <div id="spin-wrap"><input type="text" aria-valuenow="42" /></div>
    `;
    const el = document.getElementById('spin-wrap')!;
    // input.value is empty string by default, aria-valuenow should be used
    expect(summarizeElementText(el)).toBe('42');
  });

  it('summarizeElementText returns undefined for truly empty element', () => {
    document.body.innerHTML = '<div id="nothing"></div>';
    expect(summarizeElementText(document.getElementById('nothing')!)).toBeUndefined();
  });

  it('extractItemTitle falls back to summarizeElementText split', () => {
    document.body.innerHTML = '<div id="item">First Part, Second Part</div>';
    const title = extractItemTitle(document.getElementById('item')!);
    expect(title).toBe('First Part');
  });

  it('extractItemTitle returns undefined for empty item', () => {
    document.body.innerHTML = '<div id="empty-item"></div>';
    expect(extractItemTitle(document.getElementById('empty-item')!)).toBeUndefined();
  });
});
