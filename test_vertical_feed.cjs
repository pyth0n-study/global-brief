const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');

function setup({inner = null, top = 0, savedOpen = false} = {}) {
  const frames = [], handlers = {};
  const stories = [0, 100, 200].map(offsetTop => ({offsetTop, children: []}));
  const feed = {dataset: {layout: 'immersive'}, scrollTop: top, clientHeight: 100,
    style: {}, classList: {add() {}, remove() {}}, querySelectorAll: () => stories};
  const document = {querySelector(selector) {
    if (selector === 'main[data-story-feed]') return feed;
    if (selector === '.saved-stories-dialog[open]') return savedOpen ? {} : null;
    return null;
  }};
  vm.runInNewContext(readFileSync(__dirname + '/static/vertical_feed.js', 'utf8'), {
    document, window: {addEventListener: (name, callback) => { handlers[name] = callback; }},
    ResizeObserver: class { observe() {} },
    requestAnimationFrame: callback => { frames.push(callback); return frames.length; },
    cancelAnimationFrame() {}, performance: {now: () => 0}, setTimeout: callback => callback(),
  });
  return {feed, wheel(dy) {
    let prevented = false;
    handlers.wheel({deltaY: dy, deltaX: 0, deltaMode: 0, ctrlKey: false,
      target: {closest: selector => selector === 'aside,.inline-quiz' ? inner : null},
      preventDefault() { prevented = true; }});
    // Complete only the story animation, not the unrelated media-sizing frame.
    if (frames.length > 1) frames.pop()(500);
    return prevented;
  }};
}

test('a quiz that fits hands the wheel to the vertical feed', () => {
  const ui = setup({inner: {scrollHeight: 100, clientHeight: 100, scrollTop: 0}});
  assert.equal(ui.wheel(100), true);
  assert.equal(ui.feed.scrollTop, 100);
});
test('a long explanation keeps native scrolling while there is room', () => {
  const ui = setup({inner: {scrollHeight: 400, clientHeight: 100, scrollTop: 50}});
  assert.equal(ui.wheel(100), false);
  assert.equal(ui.feed.scrollTop, 0);
});
test('the bottom of an explanation advances to the next article', () => {
  const ui = setup({inner: {scrollHeight: 400, clientHeight: 100, scrollTop: 300}});
  assert.equal(ui.wheel(100), true);
  assert.equal(ui.feed.scrollTop, 100);
});
test('the top of an explanation allows returning to the previous article', () => {
  const ui = setup({top: 100, inner: {scrollHeight: 400, clientHeight: 100, scrollTop: 0}});
  assert.equal(ui.wheel(-100), true);
  assert.equal(ui.feed.scrollTop, 0);
});
test('the saved stories dialog never moves the underlying feed', () => {
  const ui = setup({savedOpen: true});
  assert.equal(ui.wheel(100), false);
  assert.equal(ui.feed.scrollTop, 0);
});
