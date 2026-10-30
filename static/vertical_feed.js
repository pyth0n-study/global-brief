/* One wheel gesture = one story. Touch uses the native vertical snap feed. */
(() => {
  const feed = document.querySelector('main[data-story-feed]');
  if (!feed) return;
  const stories = [...feed.querySelectorAll('article')];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let locked = false, delta = 0;
  const current = () => stories.reduce((best, story, i) =>
    Math.abs(story.offsetTop - feed.scrollTop) < Math.abs(stories[best].offsetTop - feed.scrollTop) ? i : best, 0);
  const move = direction => {
    if (locked || !stories.length) return;
    const target = Math.max(0, Math.min(stories.length - 1, current() + direction));
    if (target === current()) return;
    locked = true;
    feed.scrollTo({top: stories[target].offsetTop, behavior: reduced.matches ? 'instant' : 'smooth'});
    setTimeout(() => { locked = false; delta = 0; }, 750);
  };
  window.addEventListener('wheel', event => {
    if (event.ctrlKey || event.target.closest('aside,select,input,textarea') || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
    event.preventDefault();
    if (locked) return;
    delta += event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? feed.clientHeight : 1);
    if (Math.abs(delta) >= 18) { const direction = Math.sign(delta); delta = 0; move(direction); }
  }, {passive: false});
  window.addEventListener('keydown', event => {
    if (event.target.closest('aside,button,a,input,select,textarea')) return;
    const direction = {ArrowDown: 1, PageDown: 1, ArrowUp: -1, PageUp: -1}[event.key];
    if (direction) { event.preventDefault(); move(direction); }
  });
})();
