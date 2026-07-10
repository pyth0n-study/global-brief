function thumbFallback(img) {
  const wrap  = img.closest('.card-thumb');
  const bg    = wrap.dataset.bg;
  const emoji = wrap.dataset.emoji;
  wrap.outerHTML = `<div class="card-banner" style="background:${bg}">${emoji}</div>`;
}

function toggleSidebar() {
  const content = document.getElementById('sidebar-content');
  const btn     = document.querySelector('.sidebar-toggle');
  const arrow   = btn.querySelector('.sidebar-arrow');
  const isOpen  = content.classList.toggle('open');
  arrow.textContent = isOpen ? '▲' : '▼';
  btn.setAttribute('aria-expanded', isOpen);
}

document.getElementById('dark-toggle').textContent =
  document.documentElement.classList.contains('dark') ? '☀️' : '🌙';

function toggleDark() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('dark_mode', isDark ? '1' : '0');
  document.getElementById('dark-toggle').textContent = isDark ? '☀️' : '🌙';
}

window.addEventListener('load', function() {
  document.getElementById('loading-overlay').style.display = 'none';
  loadReactionCounts();
  loadBookmarkButtons();
  renderBookmarkSidebar();
});

const tooltip = document.getElementById('tooltip');
let selectedWord = '';

document.addEventListener('mouseup', function(e) {
  if (e.target.closest('.comment-form')) return;
  const selection = window.getSelection().toString().trim();
  if (selection.length > 0 && selection.length < 20) {
    selectedWord = selection;
    tooltip.style.display = 'block';
    tooltip.style.left = e.clientX + 'px';
    tooltip.style.top = (e.clientY - 50) + 'px';
  } else {
    tooltip.style.display = 'none';
  }
});

tooltip.addEventListener('click', function() {
  window.open('https://www.google.com/search?q=' + encodeURIComponent(selectedWord + ' とは'), '_blank');
  tooltip.style.display = 'none';
});

// LocalStorage で同一ブラウザの2重押し防止（キー形式: "urlhash_reaction"）
const reactedSet = new Set(JSON.parse(localStorage.getItem('user_reactions') || '[]'));

async function loadReactionCounts() {
  const allBtns = Array.from(document.querySelectorAll('.react-btn'));
  const hashes  = [...new Set(allBtns.map(b => b.dataset.hash))];
  if (!hashes.length) return;

  try {
    const res = await fetch('/api/reactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hashes })
    });
    const data = await res.json();

    allBtns.forEach(btn => {
      const h = btn.dataset.hash;
      const r = btn.dataset.reaction;
      btn.querySelector('span').textContent = (data[h] && data[h][r]) || 0;
      if (reactedSet.has(`${h}_${r}`)) btn.classList.add('reacted');
    });
  } catch (e) {}
}

async function toggleReaction(btn) {
  const hash     = btn.dataset.hash;
  const reaction = btn.dataset.reaction;
  const key      = `${hash}_${reaction}`;
  const isReacted = reactedSet.has(key);
  const action    = isReacted ? 'remove' : 'add';

  try {
    const res = await fetch('/api/react', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url_hash: hash, reaction, action })
    });
    const data = await res.json();

    btn.querySelector('span').textContent = data.count;
    if (action === 'add') {
      reactedSet.add(key);
      btn.classList.add('reacted');
      btn.style.transform = 'scale(1.25)';
      setTimeout(() => { btn.style.transform = ''; }, 160);
    } else {
      reactedSet.delete(key);
      btn.classList.remove('reacted');
    }
    localStorage.setItem('user_reactions', JSON.stringify([...reactedSet]));
  } catch (e) {}
}

function toggleComments(hash) {
  const section = document.querySelector(`.comment-section[data-hash="${hash}"]`);
  if (section.style.display === 'none') {
    section.style.display = 'block';
    loadComments(hash);
  } else {
    section.style.display = 'none';
  }
}

async function loadComments(hash) {
  const list = document.querySelector(`.comment-section[data-hash="${hash}"] .comments-list`);
  list.innerHTML = '<p class="no-comments">読み込み中...</p>';

  try {
    const res = await fetch(`/api/comments/${hash}`);
    const comments = await res.json();

    if (comments.length === 0) {
      list.innerHTML = '<p class="no-comments">まだコメントはありません。最初の一言を！</p>';
      return;
    }

    list.innerHTML = comments.map(c => `
      <div class="comment-item">
        <div class="commenter-name">👤 ${escHtml(c.nickname)}</div>
        <div class="commenter-text">${escHtml(c.body)}</div>
        <div class="commenter-time">${formatDate(c.created_at)}</div>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = '<p class="no-comments">読み込みに失敗しました</p>';
  }
}

async function submitComment(hash) {
  const section = document.querySelector(`.comment-section[data-hash="${hash}"]`);
  const nick = section.querySelector('.comment-nick-input').value.trim();
  const body = section.querySelector('.comment-body-input').value.trim();

  if (!nick || !body) {
    alert('ニックネームとコメントを入力してください');
    return;
  }

  try {
    const res = await fetch('/api/comment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url_hash: hash, nickname: nick, body })
    });
    const data = await res.json();

    if (res.ok) {
      section.querySelector('.comment-nick-input').value = '';
      section.querySelector('.comment-body-input').value = '';
      await loadComments(hash);
    } else {
      alert(data.error || 'エラーが発生しました');
    }
  } catch (e) {
    alert('送信に失敗しました');
  }
}

let bookmarks = JSON.parse(localStorage.getItem('bookmarks') || '[]');

function renderBookmarkSidebar() {
  const list  = document.getElementById('bookmark-list');
  const count = document.getElementById('bookmark-count');
  count.textContent = bookmarks.length ? `${bookmarks.length}件` : '';

  if (!bookmarks.length) {
    list.innerHTML = '<p style="font-size:12px;color:#bbb;">まだ保存した記事はありません</p>';
    return;
  }
  list.innerHTML = bookmarks.map(b => `
    <a class="bookmark-list-item" href="${escHtml(b.url)}" target="_blank">
      <span class="bookmark-category">${escHtml(b.category)}</span>
      ${escHtml(b.title.length > 28 ? b.title.slice(0, 28) + '…' : b.title)}
    </a>
  `).join('');
}

function loadBookmarkButtons() {
  const hashes = new Set(bookmarks.map(b => b.hash));
  document.querySelectorAll('.bookmark-btn').forEach(btn => {
    if (hashes.has(btn.dataset.hash)) {
      btn.classList.add('bookmarked');
      btn.textContent = '🔖 保存済み';
    }
  });
}

function toggleBookmark(btn) {
  const hash     = btn.dataset.hash;
  const idx      = bookmarks.findIndex(b => b.hash === hash);
  const isBookmarked = idx !== -1;

  if (isBookmarked) {
    bookmarks.splice(idx, 1);
    btn.classList.remove('bookmarked');
    btn.textContent = '🔖 保存';
  } else {
    bookmarks.push({
      hash,
      title:    btn.dataset.title,
      url:      btn.dataset.url,
      category: btn.dataset.category,
      savedAt:  new Date().toISOString(),
    });
    btn.classList.add('bookmarked');
    btn.textContent = '🔖 保存済み';
    btn.style.transform = 'scale(1.15)';
    setTimeout(() => { btn.style.transform = ''; }, 160);
  }

  localStorage.setItem('bookmarks', JSON.stringify(bookmarks));
  renderBookmarkSidebar();
}

function shareX(btn) {
  const url   = btn.dataset.url;
  const title = btn.dataset.title;
  window.open(
    'https://twitter.com/intent/tweet?url=' + encodeURIComponent(url) +
    '&text=' + encodeURIComponent(title + ' #GlobalBrief'),
    '_blank'
  );
}

function shareLINE(btn) {
  const url = btn.dataset.url;
  window.open(
    'https://social-plugins.line.me/lineit/share?url=' + encodeURIComponent(url),
    '_blank'
  );
}

async function copyLink(btn) {
  const url = btn.dataset.url;
  try {
    await navigator.clipboard.writeText(url);
    const orig = btn.innerHTML;
    btn.innerHTML = '✅ コピー済み';
    btn.style.borderColor = '#2e7d32';
    btn.style.color = '#2e7d32';
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.style.borderColor = '';
      btn.style.color = '';
    }, 2000);
  } catch (e) {
    const ta = document.createElement('textarea');
    ta.value = url;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    btn.innerHTML = '✅ コピー済み';
    setTimeout(() => { btn.innerHTML = '🔗 コピー'; }, 2000);
  }
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatDate(str) {
  if (!str) return '';
  try {
    return new Date(str.replace(' ', 'T')).toLocaleString('ja-JP');
  } catch (e) {
    return str;
  }
}
