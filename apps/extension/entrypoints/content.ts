import { EventCapturer } from '../src/recorder/capture';
import { captureInitialState } from '../src/recorder/initial-state';
import { getCanonicalPageUrl } from '../src/recorder/page-url';
import { AstIndex } from '../src/recorder/ast-index';
import type { RecordingEvent, FrameInfo } from '@web-agent-flow/shared-types';

export default defineContentScript({
  matches: ['<all_urls>'],
  allFrames: true,
  main() {
    // Detect if this content script is running inside an iframe
    let isIframe = false;
    try {
      isIframe = window.self !== window.top;
    } catch {
      // SecurityError accessing window.top = definitely a cross-origin iframe
      isIframe = true;
    }

    const frameInfo: FrameInfo = {
      isIframe,
      frameUrl: window.location.href,
    };

    console.info(
      `WebAgentFlow content script loaded (${isIframe ? 'iframe' : 'top frame'}): ${window.location.href}`,
    );

    let capturer: EventCapturer | null = null;

    capturer = new EventCapturer(
      {
        onEvent: (event: RecordingEvent) => {
          browser.runtime
            .sendMessage({
              type: 'RECORDING_EVENT',
              data: event,
            })
            .catch((err) => {
              console.error('Failed to send event to background:', err);
            });
        },
      },
      frameInfo,
    );

    // For iframes: auto-start capture if recording is already in progress
    // (the top frame receives START_CAPTURE, iframes may miss it on late injection)
    if (isIframe) {
      browser.runtime
        .sendMessage({ type: 'GET_STATE' })
        .then((response: { state?: { isRecording?: boolean } }) => {
          if (response?.state?.isRecording && capturer) {
            capturer.start();
            console.info('WebAgentFlow iframe: auto-started capture (recording in progress)');
            // RC4 fix: iframes may contain the actual business content — capture their
            // initial state too. Two-pass to allow async data loading.
            sendInitialState(1000);
            sendInitialState(2500);
          }
        })
        .catch(() => {
          // Ignore — extension context may not be available in some edge cases
        });
    }

    // AST index for matching events to state tree nodes.
    // Rebuilt after each initial state capture.
    const astIndex = new AstIndex();

    // Helper: capture page initial state and send to background after a delay.
    // Returns immediately; the send happens asynchronously after `delayMs`.
    // Sending from content → background wakes the MV3 service worker if needed.
    function sendInitialState(delayMs: number): void {
      setTimeout(() => {
        try {
          const initialState = captureInitialState();

          // Build AST index from the state tree so events can be matched to nodes
          if (initialState.stateTree && initialState.stateTree.length > 0) {
            astIndex.build(initialState.stateTree);
            if (capturer) capturer.setAstIndex(astIndex);
            console.info(
              `WebAgentFlow: AST index built — ${astIndex.size} leaf nodes indexed`,
            );
          }

          browser.runtime
            .sendMessage({ type: 'RECORDING_INITIAL_STATE', data: initialState })
            .catch(() => {}); // Errors silenced; background may log separately
          const nodeCount = initialState.stateTree?.length ?? initialState.fields?.length ?? 0;
          console.info(
            `WebAgentFlow: initial state sent (${delayMs}ms) — ${nodeCount} nodes from ${initialState.pageUrl}`,
          );
        } catch {
          // Ignore any DOM access errors
        }
      }, delayMs);
    }

    // Listen for messages from background script
    browser.runtime.onMessage.addListener((message, _sender, sendResponse) => {
      switch (message.type) {
        case 'PING': {
          sendResponse({ type: 'PONG', isIframe, frameUrl: window.location.href });
          break;
        }

        case 'START_CAPTURE': {
          if (capturer) {
            capturer.start();
            console.info('WebAgentFlow: started event capture');
            sendResponse({ success: true });

            // Capture initial state in every frame that actually starts recording.
            // This fixes the common shell+iframe edit-page case where the iframe is
            // already present at recording start: previously it received
            // START_CAPTURE but skipped initial-state sampling entirely.
            //
            // Two-pass:
            // - top frame: 500 / 1500 ms
            // - iframe: 1000 / 2500 ms
            // The iframe gets a slightly later window because embedded business
            // pages often hydrate later than the shell page.
            if (isIframe) {
              sendInitialState(1000);
              sendInitialState(2500);
            } else {
              sendInitialState(500);
              sendInitialState(1500);
            }
          } else {
            sendResponse({ success: false, error: 'Capturer not initialized' });
          }
          break;
        }

        case 'STOP_CAPTURE': {
          if (capturer) {
            capturer.stop();
            console.info('WebAgentFlow: stopped event capture');
            sendResponse({ success: true });
          } else {
            sendResponse({ success: false, error: 'Capturer not initialized' });
          }
          break;
        }

        case 'CAPTURE_NAVIGATE': {
          if (capturer) {
            capturer.captureNavigate();
            sendResponse({ success: true });

            // Re-capture initial state after navigation in whichever frame is
            // currently handling the business page.
            if (isIframe) {
              sendInitialState(1500);
              sendInitialState(3000);
            } else {
              sendInitialState(1000);
              sendInitialState(2500);
            }
          } else {
            sendResponse({ success: false, error: 'Capturer not initialized' });
          }
          break;
        }

        case 'GET_PAGE_INFO': {
          sendResponse({
            url: getCanonicalPageUrl(window.location.href),
            title: document.title,
            isIframe,
          });
          break;
        }

        default:
          console.warn('Unknown message type:', message.type);
      }

      return false;
    });
  },
});
