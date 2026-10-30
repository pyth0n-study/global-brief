/* One wheel gesture = one story. Touch uses the native vertical snap feed. */
(() => {
  const feed = document.querySelector('main[data-story-feed]');
  if (!feed) return;
  const stories = [...feed.querySelectorAll('article')];
  // Story transitions always animate, including visits with an old OFF preference.
  const immersive = feed.dataset.layout === 'immersive';
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
        const headerSpace = immersive ? document.querySelector('header').getBoundingClientRect().height + 14 : 0;
        const available = feed.clientHeight - contentHeight - parseFloat(style.paddingBottom) - 17 - headerSpace;
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
    const start = feed.scrollTop, end = stories[target].offsetTop;
    // Native smooth scroll can be snapped immediately by the browser.
    // Temporarily release snapping and animate the whole viewport explicitly.
    feed.style.scrollSnapType = 'none';
    feed.style.scrollBehavior = 'auto';
    feed.classList.add('is-sliding');
    const started = performance.now();
    const slide = now => {
      const progress = Math.min(1, (now - started) / 600);
      const eased = progress < .5 ? 4 * progress ** 3 : 1 - (-2 * progress + 2) ** 3 / 2;
      feed.scrollTop = start + (end - start) * eased;
      if (progress < 1) requestAnimationFrame(slide);
      else {
        feed.scrollTop = end;
        feed.style.scrollSnapType = '';
        feed.style.scrollBehavior = '';
        feed.classList.remove('is-sliding');
        setTimeout(() => { locked = false; delta = 0; }, 180);
      }
    };
    requestAnimationFrame(slide);
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
