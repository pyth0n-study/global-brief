(() => {
  const groups = [...document.querySelectorAll('.story-actions')];
  const saved = () => {
    const items = JSON.parse(localStorage.getItem('bookmarks') || '[]');
    if (!Array.isArray(items)) throw new Error('Invalid bookmarks');
    return items;
  };
  const sync = () => {
    try {
      const ids = new Set(saved().map(item => item.hash));
      groups.forEach(group => {
        const on = ids.has(group.dataset.hash), button = group.querySelector('.story-save');
        button.setAttribute('aria-pressed', String(on));
        button.setAttribute('aria-label', on ? '保存を解除' : 'あとで読むに保存');
      });
    } catch (_) { /* Storage may be unavailable; report it on the next action. */ }
  };
  groups.forEach(group => {
    let timer;
    const message = text => {
      clearTimeout(timer);
      group.querySelector('[role="status"]').textContent = text;
      timer = setTimeout(() => { group.querySelector('[role="status"]').textContent = ''; }, 2500);
    };
    group.querySelector('.story-save').addEventListener('click', () => {
      try {
        const items = saved(), index = items.findIndex(item => item.hash === group.dataset.hash);
        if (index >= 0) items.splice(index, 1);
        else items.push({hash: group.dataset.hash, title: group.dataset.title, url: group.dataset.url,
                         category: 'ニュース', savedAt: new Date().toISOString()});
        localStorage.setItem('bookmarks', JSON.stringify(items));
        sync();
        message(index >= 0 ? '保存を解除しました' : '保存しました · 一覧から見返せます');
      } catch (_) { message('このブラウザでは保存できませんでした'); }
    });
    group.querySelector('.story-share').addEventListener('click', async event => {
      const button = event.currentTarget;
      const url = new URL('/', location.origin);
      url.searchParams.set('article', group.dataset.hash);
      button.disabled = true;
      try {
        if (navigator.share && matchMedia('(pointer: coarse)').matches) {
          await navigator.share({title: group.dataset.title, url: url.href});
        } else {
          await navigator.clipboard.writeText(url.href);
          message('この記事のリンクをコピーしました');
        }
      } catch (error) {
        if (error.name !== 'AbortError') {
          // Let the user copy the same stable link if clipboard permissions fail.
          window.prompt('この記事のリンクをコピー', url.href);
        }
      } finally { button.disabled = false; }
    });
  });
  addEventListener('storage', event => { if (event.key === 'bookmarks') sync(); });
  sync();
})();
