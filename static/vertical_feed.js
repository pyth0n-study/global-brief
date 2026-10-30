/* One wheel gesture = one story. Touch uses the native vertical snap feed. */
(() => {
  const feed = document.querySelector('main[data-story-feed]');
  if (!feed) return;
  const stories = [...feed.querySelectorAll('article')];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  // Give the media all space left by this story's actual headline and controls.
  // A fixed percentage leaves large gaps on tall phones and short headlines.
  let fitFrame = 0;
  const fitMedia = () => {
    cancelAnimationFrame(fitFrame);
    fitFrame = requestAnimationFrame(() => {
      for (const story of stories) {
        const style = getComputedStyle(story);
        let contentHeight = 0;
        for (const child of story.children) {
          const css = getComputedStyle(child);
          if (css.display === 'none' || ['absolute', 'fixed'].includes(css.position)) continue;
          contentHeight += child.getBoundingClientRect().height + parseFloat(css.marginTop) + parseFloat(css.marginBottom);
        }
        const available = feed.clientHeight - contentHeight - parseFloat(style.paddingBottom) - 17;
        const height = Math.max(120, Math.floor(available));
        if (story.style.getPropertyValue('--media-height') !== height + 'px') story.style.setProperty('--media-height', height + 'px');
      }
    });
  };
  const sizeObserver = new ResizeObserver(fitMedia);
  sizeObserver.observe(feed);
  stories.forEach(story => [...story.children].forEach(child => {
    if (child.matches('h1,nav,.credit,.count,.status,.thinking-teaser')) sizeObserver.observe(child);
  }));
  document.fonts?.ready.then(fitMedia);
  fitMedia();
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
