import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  addDomMutations,
  addEvent,
  clearEvents,
  clearState,
  createInitialState,
  loadState,
  saveState,
  setInitialState,
  startRecording,
  stopRecording,
} from '../recorder/state';

const storageMock = {
  setItem: vi.fn(),
  getItem: vi.fn(),
  removeItem: vi.fn(),
};

vi.stubGlobal('storage', storageMock);

describe('recorder state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates the default empty recorder state', () => {
    expect(createInitialState()).toEqual({
      isRecording: false,
      events: [],
      domMutations: [],
      startTime: null,
      initialUrl: null,
      initialTitle: null,
      initialState: null,
      initialStateSource: null,
    });
  });

  it('saves, loads, and clears state through storage', async () => {
    const state = createInitialState();
    storageMock.getItem.mockResolvedValueOnce(state);

    await saveState(state);
    expect(storageMock.setItem).toHaveBeenCalled();

    await expect(loadState()).resolves.toEqual(state);

    await clearState();
    expect(storageMock.removeItem).toHaveBeenCalled();
  });

  it('falls back to a fresh state when storage is empty', async () => {
    storageMock.getItem.mockResolvedValueOnce(null);
    await expect(loadState()).resolves.toEqual(createInitialState());
  });

  it('starts and stops recording while resetting transient fields', () => {
    const started = startRecording(createInitialState(), 'https://example.com', 'Example');
    expect(started.isRecording).toBe(true);
    expect(started.initialUrl).toBe('https://example.com');
    expect(started.initialTitle).toBe('Example');
    expect(started.events).toEqual([]);
    expect(started.domMutations).toEqual([]);
    expect(started.startTime).toBeTypeOf('number');

    expect(stopRecording(started).isRecording).toBe(false);
  });

  it('adds events and DOM mutations only while recording', () => {
    const idle = createInitialState();
    const event = { id: 'e0', type: 'click', timestamp: 1, url: 'https://example.com' } as const;
    const mutation = { type: 'attributes', target: { tag: 'button' } } as never;

    expect(addEvent(idle, event)).toBe(idle);
    expect(addDomMutations(idle, [mutation])).toBe(idle);

    const active = startRecording(idle, 'https://example.com');
    const withEvent = addEvent(active, event);
    expect(withEvent.events).toEqual([event]);

    const withMutations = addDomMutations(withEvent, [mutation]);
    expect(withMutations.domMutations).toHaveLength(1);
    expect(clearEvents(withMutations).events).toEqual([]);
  });

  it('stores first initial state and backfills missing url/title', () => {
    const active = startRecording(createInitialState(), '', '');
    const initialState = {
      pageUrl: 'https://example.com/page',
      pageTitle: 'Example Page',
      capturedAt: 10,
      stateTree: [{ type: 'input', label: 'Name', value: 'Alice', required: true }],
    };

    const next = setInitialState(active, initialState);
    expect(next.initialState).toEqual(initialState);
    expect(next.initialUrl).toBe('https://example.com/page');
    expect(next.initialTitle).toBe('Example Page');
    expect(next.initialStateSource?.score).toBeGreaterThan(0);
  });

  it('prefers higher-scoring snapshots from the same frame and merges iframe snapshots', () => {
    const base = startRecording(createInitialState(), 'https://top.example.com', 'Top');
    const topFrame = {
      pageUrl: 'https://top.example.com',
      pageTitle: 'Top',
      capturedAt: 1,
      stateTree: [{ type: 'section', label: 'TopNav', children: [{ type: 'link', label: 'Home', value: '/' }] }],
    };
    const improvedTopFrame = {
      pageUrl: 'https://top.example.com',
      pageTitle: 'Top',
      capturedAt: 2,
      stateTree: [{ type: 'section', label: 'TopNav', children: [{ type: 'link', label: 'Home', value: '/' }, { type: 'button', label: 'Search', value: 'go', required: true }] }],
    };
    const iframeState = {
      pageUrl: 'https://frame.example.com',
      pageTitle: 'Frame',
      capturedAt: 3,
      stateTree: [{ type: 'button', label: 'Submit', localHtml: '<button>Submit</button>' }],
    };

    const withTop = setInitialState(base, topFrame, { frameId: 0, senderUrl: 'https://top.example.com' });
    const withImprovedTop = setInitialState(withTop, improvedTopFrame, { frameId: 0, senderUrl: 'https://top.example.com' });
    expect(withImprovedTop.initialState?.stateTree?.[0].children).toHaveLength(2);

    const withIframe = setInitialState(withImprovedTop, iframeState, { frameId: 2, senderUrl: 'https://frame.example.com' });
    expect(withIframe.initialState?.stateTree).toHaveLength(2);
    expect(withIframe.initialState?.stateTree?.[1]).toMatchObject({
      type: 'section',
      blockType: 'iframe-content',
      label: 'Frame',
    });
  });
});
