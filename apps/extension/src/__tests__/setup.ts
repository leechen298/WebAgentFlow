/**
 * Test setup — patches jsdom limitations for DOM-heavy tests.
 *
 * jsdom doesn't compute CSS layout, so offsetWidth/offsetHeight/offsetParent
 * are always 0/null. We patch them to return reasonable defaults so that
 * isVisible() and similar layout-dependent checks work correctly.
 *
 * Elements with inline `display: none` are still treated as invisible.
 */

function hasInlineHidden(el: HTMLElement): boolean {
  const style = el.style;
  return style.display === 'none' || style.visibility === 'hidden';
}

Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
  get(this: HTMLElement) {
    if (hasInlineHidden(this)) return null;
    return this === document.body ? null : document.body;
  },
  configurable: true,
});

Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
  get(this: HTMLElement) {
    if (hasInlineHidden(this)) return 0;
    return 100;
  },
  configurable: true,
});

Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
  get(this: HTMLElement) {
    if (hasInlineHidden(this)) return 0;
    return 50;
  },
  configurable: true,
});
