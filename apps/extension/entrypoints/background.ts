import {
  loadState,
  saveState,
  startRecording,
  stopRecording,
  addEvent,
  createInitialState,
  setInitialState,
} from '../src/recorder/state';
import type { RecordingEvent, PageInitialState } from '@web-agent-flow/shared-types';
import type { RecorderState } from '../src/recorder/state';

export default defineBackground(() => {
  // Keep state in memory for quick access
  let currentState: RecorderState = createInitialState();

  // Initialize state from storage on startup
  async function initializeState() {
    currentState = await loadState();
    console.info('Background initialized with state:', currentState);
    updateBadge();
  }

  initializeState();

  // Update extension badge based on recording state
  function updateBadge() {
    if (currentState.isRecording) {
      browser.action.setBadgeText({ text: 'REC' });
      browser.action.setBadgeBackgroundColor({ color: '#ff4444' });
    } else {
      browser.action.setBadgeText({ text: '' });
    }
  }

  // Inject content script into a tab if not already injected
  async function ensureContentScriptInjected(tabId: number): Promise<boolean> {
    try {
      // First ping the tab to see if content script is already there
      const response = await browser.tabs.sendMessage(tabId, { type: 'PING' }).catch(() => null);
      if (response?.type === 'PONG') {
        return true;
      }
    } catch {
      // Content script not present, need to inject
    }

    try {
      // Inject the content script into all frames (top + iframes)
      await browser.scripting.executeScript({
        target: { tabId, allFrames: true },
        files: ['/content-scripts/content.js'],
      });
      // Wait a bit for the script to initialize
      await new Promise((resolve) => setTimeout(resolve, 100));
      return true;
    } catch (error) {
      console.error('Failed to inject content script:', error);
      return false;
    }
  }

  // Get current tab info
  async function getActiveTab(): Promise<browser.Tabs.Tab | null> {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    return tab || null;
  }

  // Listen for messages from popup or content script
  browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    (async () => {
      try {
        console.log('Background received message:', message.type);

        switch (message.type) {
          // === Messages from content script ===
          case 'RECORDING_EVENT': {
            const event = message.data as RecordingEvent;
            currentState = addEvent(currentState, event);
            await saveState(currentState);
            sendResponse({ success: true });
            break;
          }

          case 'RECORDING_INITIAL_STATE': {
            // NOTE: No isRecording guard here.
            // The guard was removed because of a MV3 service worker race condition:
            // if the SW is killed and restarted, initializeState() is async and
            // currentState.isRecording may be false until storage loads. We trust
            // that this message is only sent by the content script immediately after
            // START_CAPTURE, so any received initial state is valid for the current
            // recording session.
            const newInitialState = message.data as PageInitialState;
            const before = currentState.initialState;
            currentState = setInitialState(currentState, newInitialState, {
              frameId: sender.frameId,
              senderUrl: sender.url ?? null,
            });
            await saveState(currentState);
            const action = currentState.initialState === before ? 'kept' : 'stored';
            const source = currentState.initialStateSource;
            const nodeCount = newInitialState.stateTree?.length ?? newInitialState.fields?.length ?? 0;
            console.info(
              `Background: ${action} initial state — ${nodeCount} nodes from ${newInitialState.pageUrl} (frameId=${sender.frameId ?? 'n/a'}, score=${source?.score ?? 'n/a'})`,
            );
            sendResponse({ success: true });
            break;
          }

          // === Messages from popup ===
          case 'GET_STATE': {
            sendResponse({ success: true, state: currentState });
            break;
          }

          case 'START_RECORDING': {
            const tab = await getActiveTab();
            if (!tab?.id || !tab.url) {
              sendResponse({ success: false, error: 'No active tab found' });
              return;
            }

            // Inject content script if needed
            const injected = await ensureContentScriptInjected(tab.id);
            if (!injected) {
              sendResponse({ success: false, error: 'Failed to inject content script' });
              return;
            }

            // Get page info
            let pageInfo: { url: string; title?: string } = { url: tab.url };
            try {
              pageInfo = await browser.tabs.sendMessage(tab.id, { type: 'GET_PAGE_INFO' });
            } catch {
              // Use tab info as fallback
              pageInfo = { url: tab.url, title: tab.title };
            }

            // Update state
            currentState = startRecording(currentState, pageInfo.url, pageInfo.title);
            await saveState(currentState);

            // Start capture in content script
            await browser.tabs.sendMessage(tab.id, { type: 'START_CAPTURE' });

            updateBadge();
            sendResponse({ success: true, state: currentState });
            break;
          }

          case 'STOP_RECORDING': {
            const tab = await getActiveTab();
            if (tab?.id) {
              try {
                await browser.tabs.sendMessage(tab.id, { type: 'STOP_CAPTURE' });
              } catch {
                // Ignore if content script isn't available
              }
            }

            currentState = stopRecording(currentState);
            await saveState(currentState);
            updateBadge();
            sendResponse({ success: true, state: currentState });
            break;
          }

          case 'CLEAR_RECORDING': {
            currentState = { ...createInitialState(), isRecording: false };
            await saveState(currentState);
            updateBadge();
            sendResponse({ success: true, state: currentState });
            break;
          }

          default:
            console.warn('Unknown message type:', message.type);
            sendResponse({ success: false, error: 'Unknown message type' });
        }
      } catch (error) {
        console.error('Error handling message:', error);
        sendResponse({ success: false, error: String(error) });
      }
    })();

    return true; // Keep port open for async response
  });

  // Listen for tab updates to capture navigation events while recording
  browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (!currentState.isRecording) {
      return;
    }

    if (changeInfo.status === 'complete' && tab.url) {
      // Send message to content script to capture navigation
      browser.tabs.sendMessage(tabId, { type: 'CAPTURE_NAVIGATE' }).catch(() => {
        // Ignore errors
      });
    }
  });
});
