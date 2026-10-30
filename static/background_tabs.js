(() => {
  const tabs = [...document.querySelectorAll('.context-tabs [role="tab"]')];
  if (!tabs.length) return;
  const choose = (name, updateUrl = false) => {
    tabs.forEach(tab => {
      const selected = tab.getAttribute('aria-controls') === name;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
      document.getElementById(tab.getAttribute('aria-controls')).hidden = !selected;
    });
    document.querySelector('input[name="tab"]').value = name;
    const clear = document.querySelector('.clear-filters');
    if (clear) clear.href = '/background?tab=' + name;
    if (updateUrl) {
      const url = new URL(location.href);
      if (name === 'archive') url.searchParams.set('tab', 'archive');
      else url.searchParams.delete('tab');
      url.hash = '';
      history.pushState(null, '', url);
    }
  };
  const fromUrl = () => {
    const hash = location.hash;
    const name = hash === '#archive' ? 'archive' : hash === '#basics' || hash.startsWith('#guide-') ? 'basics'
      : new URLSearchParams(location.search).get('tab') === 'archive' ? 'archive' : 'basics';
    choose(name);
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
  };
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => choose(tab.getAttribute('aria-controls'), true));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      tabs[next].focus();
      choose(tabs[next].getAttribute('aria-controls'), true);
    });
  });
  addEventListener('popstate', fromUrl);
  addEventListener('hashchange', fromUrl);
  fromUrl();
})();
