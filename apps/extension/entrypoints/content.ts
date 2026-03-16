export default defineContentScript({
  matches: ['<all_urls>'],
  main() {
    console.info('WebAgentFlow content script loaded');
  },
});
