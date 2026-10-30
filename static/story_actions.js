(() => {
  const groups = [...document.querySelectorAll('.story-actions')];
  const saved = () => {
    const items = JSON.parse(localStorage.getItem('bookmarks') || '[]');
    if (!Array.isArray(items)) throw new Error('Invalid bookmarks');
    return items;
  };
  const panel = document.querySelector('.saved-stories-dialog');
  const opener = document.querySelector('.saved-stories-open');
  const renderSaved = () => {
    if (!panel) return;
    const list = panel.querySelector('.saved-stories-list');
    list.replaceChildren();
    try {
      const items = saved().filter(item => item && typeof item.title === 'string' && /^[a-f0-9]{32}$/.test(item.hash));
      opener.querySelector('.saved-stories-count').textContent = items.length;
      if (!items.length) {
        const empty = document.createElement('p');
        empty.className = 'saved-stories-empty';
        empty.textContent = '保存した記事はまだありません。カードの保存アイコンから追加できます。';
        list.append(empty);
      }
      items.slice().reverse().forEach(item => {
        const link = document.createElement('a');
        link.href = '/?article=' + encodeURIComponent(item.hash);
        link.textContent = item.title;
        list.append(link);
      });
    } catch (_) {
      list.textContent = 'このブラウザの保存データを読み込めませんでした。';
    }
  };
  if (panel && opener) {
    opener.addEventListener('click', () => { renderSaved(); panel.showModal(); });
    panel.querySelector('.saved-stories-close').addEventListener('click', () => panel.close());
    panel.addEventListener('click', event => {
      const rect = panel.getBoundingClientRect();
      if (event.target === panel && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) panel.close();
    });
    panel.addEventListener('close', () => opener.focus());
  }
  const sync = () => {
    try {
      const ids = new Set(saved().map(item => item.hash));
      groups.forEach(group => {
        const on = ids.has(group.dataset.hash), button = group.querySelector('.story-save');
        button.setAttribute('aria-pressed', String(on));
        button.setAttribute('aria-label', on ? '保存を解除' : 'あとで読むに保存');
      });
    } catch (_) { /* Storage may be unavailable; report it on the next action. */ }
    renderSaved();
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
        message(index >= 0 ? '保存を解除しました' : '保存しました');
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
