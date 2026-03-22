import { EventCapturer } from '../src/recorder/capture';
import type { RecordingEvent } from '@web-agent-flow/shared-types';

export default defineContentScript({
  matches: ['<all_urls>'],
  main() {
    console.info('WebAgentFlow content script loaded');

    let capturer: EventCapturer | null = null;

    // Initialize capturer
    capturer = new EventCapturer({
      onEvent: (event: RecordingEvent) => {
        // Send event to background script
        browser.runtime.sendMessage({
          type: 'RECORDING_EVENT',
          data: event,
        }).catch((err) => {
          console.error('Failed to send event to background:', err);
        });
      },
    });

    // Listen for messages from background script
    browser.runtime.onMessage.addListener((message, _sender, sendResponse) => {
      console.log('Content script received message:', message);

      switch (message.type) {
        case 'PING': {
          sendResponse({ type: 'PONG' });
          break;
        }

        case 'START_CAPTURE': {
          if (capturer) {
            capturer.start();
            console.info('Started event capture');
            sendResponse({ success: true });
          } else {
            sendResponse({ success: false, error: 'Capturer not initialized' });
          }
          break;
        }

        case 'STOP_CAPTURE': {
          if (capturer) {
            capturer.stop();
            console.info('Stopped event capture');
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
          });
          break;
        }

        default:
          console.warn('Unknown message type:', message.type);
      }

      return false; // Don't keep the port open
    });
  },
});
