import { EventCapturer } from '../src/recorder/capture';
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
          }
        })
        .catch(() => {
          // Ignore — extension context may not be available in some edge cases
        });
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
          } else {
            sendResponse({ success: false, error: 'Capturer not initialized' });
          }
          break;
        }

        case 'GET_PAGE_INFO': {
          sendResponse({
            url: window.location.href,
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
