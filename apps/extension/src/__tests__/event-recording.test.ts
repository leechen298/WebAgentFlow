/**
 * Tests for event recording with IDs and AST matching integration.
 *
 * Covers:
 *   1. Events get unique sequential IDs
 *   2. resetEventCounter resets the counter
 *   3. Events carry astMatch when index is available
 *   4. Events without AST index have no astMatch
 *   5. Events are in chronological order
 *   6. All event types (click, input, change) are captured with IDs
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { createRecordingEvent, resetEventCounter, setEventIdPrefix } from '../recorder/events';
import type { AstMatch } from '@web-agent-flow/shared-types';

describe('createRecordingEvent — event IDs', () => {
  beforeEach(() => {
    resetEventCounter();
  });

  it('assigns sequential IDs starting from e0', () => {
    const e1 = createRecordingEvent('click', 'http://example.com');
    const e2 = createRecordingEvent('input', 'http://example.com');
    const e3 = createRecordingEvent('change', 'http://example.com');

    expect(e1.id).toBe('e0');
    expect(e2.id).toBe('e1');
    expect(e3.id).toBe('e2');
  });

  it('resets counter on resetEventCounter()', () => {
    createRecordingEvent('click', 'http://example.com');
    createRecordingEvent('click', 'http://example.com');

    resetEventCounter();

    const e = createRecordingEvent('click', 'http://example.com');
    expect(e.id).toBe('e0');
  });

  it('includes astMatch when provided', () => {
    const match: AstMatch = {
      confidence: 'exact',
      nodeId: 'n5',
      nodePath: '0.2',
      nodeType: 'button',
      nodeLabel: 'Submit',
    };

    const e = createRecordingEvent('click', 'http://example.com', {
      astMatch: match,
    });

    expect(e.astMatch).toBeDefined();
    expect(e.astMatch!.confidence).toBe('exact');
    expect(e.astMatch!.nodeId).toBe('n5');
    expect(e.astMatch!.nodeLabel).toBe('Submit');
  });

  it('has no astMatch when not provided', () => {
    const e = createRecordingEvent('click', 'http://example.com');
    expect(e.astMatch).toBeUndefined();
  });

  it('preserves all standard fields alongside id', () => {
    const e = createRecordingEvent('input', 'http://example.com', {
      title: 'Test Page',
      value: 'hello',
      target: { tag: 'input' },
      fieldContext: {
        containerType: 'form-item',
        fieldLabel: 'Name',
      },
    });

    expect(e.id).toBe('e0');
    expect(e.type).toBe('input');
    expect(e.url).toBe('http://example.com');
    expect(e.title).toBe('Test Page');
    expect(e.value).toBe('hello');
    expect(e.target?.tag).toBe('input');
    expect(e.fieldContext?.fieldLabel).toBe('Name');
    expect(e.timestamp).toBeGreaterThan(0);
  });

  it('generates events in chronological order', () => {
    const events = [];
    for (let i = 0; i < 5; i++) {
      events.push(createRecordingEvent('click', 'http://example.com'));
    }

    for (let i = 1; i < events.length; i++) {
      expect(events[i].timestamp).toBeGreaterThanOrEqual(events[i - 1].timestamp);
    }

    // IDs are sequential
    expect(events.map(e => e.id)).toEqual(['e0', 'e1', 'e2', 'e3', 'e4']);
  });

  it('supports navigate events with ID', () => {
    const e = createRecordingEvent('navigate', 'http://example.com/page', {
      title: 'Page Title',
    });

    expect(e.id).toBe('e0');
    expect(e.type).toBe('navigate');
    expect(e.url).toBe('http://example.com/page');
    expect(e.title).toBe('Page Title');
  });

  it('supports richtext-input events with ID and astMatch', () => {
    const match: AstMatch = {
      confidence: 'ancestor',
      nodeId: 'n10',
      nodePath: '1.0',
      nodeType: 'richtext',
      nodeLabel: 'Content Editor',
    };

    const e = createRecordingEvent('richtext-input', 'http://example.com', {
      value: 'Some rich text',
      htmlContent: '<p>Some rich text</p>',
      astMatch: match,
    });

    expect(e.id).toBe('e0');
    expect(e.type).toBe('richtext-input');
    expect(e.astMatch?.confidence).toBe('ancestor');
    expect(e.astMatch?.nodeType).toBe('richtext');
  });
});

describe('frame-aware event IDs', () => {
  beforeEach(() => {
    resetEventCounter();
    setEventIdPrefix('e'); // reset to default
  });

  it('uses "f" prefix for iframe events', () => {
    setEventIdPrefix('f');
    const e1 = createRecordingEvent('click', 'http://example.com');
    const e2 = createRecordingEvent('input', 'http://example.com');

    expect(e1.id).toBe('f0');
    expect(e2.id).toBe('f1');
  });

  it('top frame and iframe produce non-colliding IDs', () => {
    // Simulate top frame
    setEventIdPrefix('e');
    const top1 = createRecordingEvent('click', 'http://example.com');
    const top2 = createRecordingEvent('click', 'http://example.com');

    // Simulate iframe (separate counter in real code, but test prefix)
    setEventIdPrefix('f');
    resetEventCounter();
    const iframe1 = createRecordingEvent('click', 'http://example.com');
    const iframe2 = createRecordingEvent('click', 'http://example.com');

    // All IDs are unique
    const ids = [top1.id, top2.id, iframe1.id, iframe2.id];
    expect(new Set(ids).size).toBe(4);
    expect(ids).toEqual(['e0', 'e1', 'f0', 'f1']);
  });

  it('resetEventCounter does not change prefix', () => {
    setEventIdPrefix('f');
    createRecordingEvent('click', 'http://example.com');
    resetEventCounter();
    const e = createRecordingEvent('click', 'http://example.com');
    expect(e.id).toBe('f0'); // prefix preserved after reset
  });
});

describe('event never lost on astMatch failure', () => {
  beforeEach(() => {
    resetEventCounter();
    setEventIdPrefix('e');
  });

  it('event with confidence:none still has all core fields', () => {
    const match: AstMatch = {
      confidence: 'none',
      ancestorChain: 'span.icon > button.unknown > div.container',
      areaLabel: 'Settings Panel',
    };

    const e = createRecordingEvent('click', 'http://example.com/settings', {
      title: 'Settings',
      target: { tag: 'span' },
      fieldContext: { containerType: 'unknown' },
      astMatch: match,
    });

    // Core fields intact
    expect(e.id).toBe('e0');
    expect(e.type).toBe('click');
    expect(e.url).toBe('http://example.com/settings');
    expect(e.timestamp).toBeGreaterThan(0);
    expect(e.target?.tag).toBe('span');

    // AST fallback info present
    expect(e.astMatch?.confidence).toBe('none');
    expect(e.astMatch?.ancestorChain).toContain('span.icon');
    expect(e.astMatch?.areaLabel).toBe('Settings Panel');

    // No node fields
    expect(e.astMatch?.nodeId).toBeUndefined();
    expect(e.astMatch?.nodePath).toBeUndefined();
  });

  it('event without astMatch at all still has all core fields', () => {
    const e = createRecordingEvent('input', 'http://example.com', {
      value: 'test',
      target: { tag: 'input' },
    });

    expect(e.id).toBe('e0');
    expect(e.type).toBe('input');
    expect(e.value).toBe('test');
    expect(e.target?.tag).toBe('input');
    expect(e.astMatch).toBeUndefined();
  });
});
