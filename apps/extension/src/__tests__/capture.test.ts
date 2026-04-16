import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  createRecordingEvent,
  getTargetInfo,
  resetEventCounter,
} = vi.hoisted(() => ({
  createRecordingEvent: vi.fn((type: string, url: string, options: Record<string, unknown> = {}) => ({
    id: `${type}-id`,
    type,
    url,
    ...options,
  })),
  getTargetInfo: vi.fn((element: Element) => ({ tag: element.tagName.toLowerCase() })),
  resetEventCounter: vi.fn(),
}));

const { getFieldContext } = vi.hoisted(() => ({
  getFieldContext: vi.fn(() => ({ fieldLabel: 'Field' })),
}));

vi.mock('../recorder/events', () => ({
  createRecordingEvent,
  getTargetInfo,
  resetEventCounter,
}));

vi.mock('../recorder/context', () => ({
  getFieldContext,
}));

import { EventCapturer } from '../recorder/capture';

describe('EventCapturer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    document.title = 'Capture Page';
    document.body.innerHTML = '';
  });

  it('starts capture, emits navigate, and stops cleanly', () => {
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent }, { isIframe: false, frameUrl: 'https://frame.example.com' });

    capturer.start();

    expect(resetEventCounter).toHaveBeenCalledOnce();
    expect(createRecordingEvent).toHaveBeenCalledWith('navigate', window.location.href, {
      title: 'Capture Page',
      frameInfo: { isIframe: false, frameUrl: 'https://frame.example.com' },
    });
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'navigate' }));

    capturer.stop();
    document.body.innerHTML = '<button id="after-stop">After</button>';
    document.getElementById('after-stop')!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(onEvent).toHaveBeenCalledTimes(1);
  });

  it('captures click events and ignores extension-owned elements', () => {
    document.body.innerHTML = `
      <button id="cta">Save</button>
      <div id="webagentflow-modal"><button id="inner">Ignore</button></div>
    `;
    const onEvent = vi.fn();
    const matchElement = vi.fn(() => ({ confidence: 'exact', nodeId: 'n1' }));
    const capturer = new EventCapturer({ onEvent });
    capturer.setAstIndex({ matchElement } as never);
    capturer.start();
    onEvent.mockClear();

    document.getElementById('cta')!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(getTargetInfo).toHaveBeenCalled();
    expect(getFieldContext).toHaveBeenCalled();
    expect(matchElement).toHaveBeenCalled();
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'click', astMatch: { confidence: 'exact', nodeId: 'n1' } }));

    onEvent.mockClear();
    document.getElementById('inner')!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(onEvent).not.toHaveBeenCalled();
  });

  it('debounces input events and turns a follow-up change into one final change event', () => {
    document.body.innerHTML = '<input id="name" value="Alice" />';
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    const input = document.getElementById('name') as HTMLInputElement;
    input.value = 'Alice 1';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    vi.advanceTimersByTime(300);
    input.value = 'Alice 2';
    input.dispatchEvent(new Event('change', { bubbles: true }));

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'change', value: 'Alice 2' }));
  });

  it('captures debounced rich text input and deduplicates identical blur emissions', () => {
    document.body.innerHTML = '<div id="editor"><p>Hello world</p></div>';
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    const editor = document.getElementById('editor') as HTMLElement;
    editor.contentEditable = 'true';
    editor.dispatchEvent(new Event('input', { bubbles: true }));
    vi.advanceTimersByTime(801);

    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({
      type: 'richtext-input',
      value: 'Hello world',
      htmlContent: '<p>Hello world</p>',
      target: expect.objectContaining({ isRichText: true, role: 'rich-text' }),
    }));

    onEvent.mockClear();
    editor.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
    expect(onEvent).not.toHaveBeenCalled();
  });

  it('is idempotent on repeated start and handles non-form change events', () => {
    document.body.innerHTML = '<div id="editable">hello</div>';
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });

    capturer.start();
    capturer.start();
    expect(resetEventCounter).toHaveBeenCalledTimes(1);

    onEvent.mockClear();
    const editable = document.getElementById('editable') as HTMLElement;
    editable.dispatchEvent(new Event('change', { bubbles: true }));
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'change', value: null }));
  });

  it('captures rich text inside same-origin iframes', () => {
    document.body.innerHTML = '<iframe id="editor-frame"></iframe>';
    const iframe = document.getElementById('editor-frame') as HTMLIFrameElement;
    const iframeDoc = document.implementation.createHTMLDocument('frame');
    iframeDoc.body.innerHTML = '<div id="rt">Frame text</div>';
    const rich = iframeDoc.getElementById('rt') as HTMLElement;
    rich.contentEditable = 'true';

    Object.defineProperty(iframe, 'contentDocument', { value: iframeDoc, configurable: true });

    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    rich.dispatchEvent(new Event('input', { bubbles: true }));
    vi.advanceTimersByTime(801);
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'richtext-input', value: 'Frame text' }));

    onEvent.mockClear();
    rich.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
    expect(onEvent).not.toHaveBeenCalled();
  });

  it('captures iframe body rich text and skips empty content', () => {
    document.body.innerHTML = '<iframe id="body-frame"></iframe>';
    const iframe = document.getElementById('body-frame') as HTMLIFrameElement;
    const iframeDoc = document.implementation.createHTMLDocument('body-frame');
    iframeDoc.body.contentEditable = 'true';
    iframeDoc.body.innerHTML = '<p>Body text</p>';
    Object.defineProperty(iframe, 'contentDocument', { value: iframeDoc, configurable: true });

    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    iframeDoc.body.dispatchEvent(new Event('input', { bubbles: true }));
    vi.advanceTimersByTime(801);
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'richtext-input', value: 'Body text' }));

    onEvent.mockClear();
    iframeDoc.body.textContent = '';
    iframeDoc.body.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
    expect(onEvent).not.toHaveBeenCalled();
  });

  it('ignores cross-origin iframe attachment failures and disconnects cleanly', () => {
    document.body.innerHTML = '<iframe id="x"></iframe>';
    const iframe = document.getElementById('x') as HTMLIFrameElement;
    Object.defineProperty(iframe, 'contentDocument', {
      configurable: true,
      get() {
        throw new DOMException('denied', 'SecurityError');
      },
    });

    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    expect(() => capturer.start()).not.toThrow();
    expect(() => capturer.stop()).not.toThrow();
  });

  it('emits input event after debounce timeout when no change follows', () => {
    document.body.innerHTML = '<input id="field" />';
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    const input = document.getElementById('field') as HTMLInputElement;
    input.value = 'typed text';
    input.dispatchEvent(new Event('input', { bubbles: true }));

    // Advance past the 600ms debounce
    vi.advanceTimersByTime(601);

    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'input', value: 'typed text' }));
    capturer.stop();
  });

  it('handles input events on non-form, non-richtext elements (no-op)', () => {
    document.body.innerHTML = '<div id="plain">text</div>';
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    const div = document.getElementById('plain')!;
    div.dispatchEvent(new Event('input', { bubbles: true }));

    vi.advanceTimersByTime(1000);
    // No event should be emitted for a plain div input event
    expect(onEvent).not.toHaveBeenCalled();
    capturer.stop();
  });

  it('handles change events on non-form elements (emits change directly)', () => {
    document.body.innerHTML = '<div id="custom-ctrl">val</div>';
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    const div = document.getElementById('custom-ctrl')!;
    div.dispatchEvent(new Event('change', { bubbles: true }));

    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'change' }));
    capturer.stop();
  });

  it('handles focusout on non-richtext elements (no-op)', () => {
    document.body.innerHTML = '<input id="txt" />';
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    const input = document.getElementById('txt')!;
    input.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));

    vi.advanceTimersByTime(1000);
    // focusout on a regular input should not trigger richtext capture
    expect(onEvent).not.toHaveBeenCalled();
    capturer.stop();
  });

  it('does not emit richtext-input for empty content', () => {
    document.body.innerHTML = '<div id="editor" contenteditable="true"></div>';
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    const editor = document.getElementById('editor') as HTMLElement;
    editor.dispatchEvent(new Event('input', { bubbles: true }));
    vi.advanceTimersByTime(801);

    // Empty text should not emit richtext-input
    expect(onEvent).not.toHaveBeenCalled();
    capturer.stop();
  });

  it('handles events with null target gracefully', () => {
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    // Dispatch events that might have null-ish targets — they should be filtered
    // The handler checks !target and returns early
    const inputEvent = new Event('input', { bubbles: true });
    Object.defineProperty(inputEvent, 'target', { value: null });
    document.dispatchEvent(inputEvent);

    const changeEvent = new Event('change', { bubbles: true });
    Object.defineProperty(changeEvent, 'target', { value: null });
    document.dispatchEvent(changeEvent);

    const focusoutEvent = new FocusEvent('focusout', { bubbles: true });
    Object.defineProperty(focusoutEvent, 'target', { value: null });
    document.dispatchEvent(focusoutEvent);

    vi.advanceTimersByTime(1000);
    expect(onEvent).not.toHaveBeenCalled();
    capturer.stop();
  });

  it('captureNavigate can be called explicitly after start', () => {
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    capturer.captureNavigate();
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'navigate' }));
    capturer.stop();
  });

  it('stop is idempotent — calling stop twice does not throw', () => {
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    expect(() => capturer.stop()).not.toThrow();
    expect(() => capturer.stop()).not.toThrow();
  });

  it('attaches mutation observer fallback to iframe body with designMode', () => {
    document.body.innerHTML = '<iframe id="dm-frame"></iframe>';
    const iframe = document.getElementById('dm-frame') as HTMLIFrameElement;
    const iframeDoc = document.implementation.createHTMLDocument('dm');
    iframeDoc.body.innerHTML = '<p>Design mode text</p>';
    Object.defineProperty(iframeDoc, 'designMode', { value: 'on', writable: true });
    Object.defineProperty(iframe, 'contentDocument', { value: iframeDoc, configurable: true });

    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    expect(() => capturer.start()).not.toThrow();

    onEvent.mockClear();
    // Trigger input in the designMode body
    iframeDoc.body.dispatchEvent(new Event('input', { bubbles: true }));
    vi.advanceTimersByTime(801);

    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'richtext-input' }));
    capturer.stop();
  });

  it('iframe body becomes contenteditable after initial attachment', () => {
    document.body.innerHTML = '<iframe id="delayed-ce"></iframe>';
    const iframe = document.getElementById('delayed-ce') as HTMLIFrameElement;
    const iframeDoc = document.implementation.createHTMLDocument('delayed');
    iframeDoc.body.innerHTML = '<p>Will be editable</p>';
    Object.defineProperty(iframe, 'contentDocument', { value: iframeDoc, configurable: true });

    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();

    // Initially body is NOT contenteditable — the attrObserver watches for it
    // Now set contenteditable
    iframeDoc.body.contentEditable = 'true';

    // The MutationObserver on body attributes should fire
    // We need to flush the mutation observer
    onEvent.mockClear();
    iframeDoc.body.dispatchEvent(new Event('input', { bubbles: true }));
    vi.advanceTimersByTime(801);

    // Should capture richtext-input from the now-editable body
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'richtext-input', value: 'Will be editable' }));
    capturer.stop();
  });

  it('extension element detection via webagentflow-extension class', () => {
    document.body.innerHTML = `
      <div class="webagentflow-extension"><button id="ext-btn">Ext</button></div>
      <button id="normal-btn">Normal</button>
    `;
    const onEvent = vi.fn();
    const capturer = new EventCapturer({ onEvent });
    capturer.start();
    onEvent.mockClear();

    document.getElementById('ext-btn')!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(onEvent).not.toHaveBeenCalled();

    document.getElementById('normal-btn')!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({ type: 'click' }));
    capturer.stop();
  });
});
