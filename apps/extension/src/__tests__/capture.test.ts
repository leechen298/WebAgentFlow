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
});
