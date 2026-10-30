"""Source article archive. Classification is explicit keyword matching, not history generation."""
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

COUNTRIES = {
    'spain': ('スペイン', ('スペイン',)), 'usa': ('アメリカ', ('アメリカ', '米国', '米軍', '米中間選挙')),
    'france': ('フランス', ('フランス', '仏BNP', '仏極右')), 'israel': ('イスラエル', ('イスラエル',)),
    'korea': ('韓国', ('韓国',)), 'japan': ('日本', ('日本', '日中', '小泉防衛相', '沖縄', '嘉手納')),
    'china': ('中国', ('中国', '日中')), 'brazil': ('ブラジル', ('ブラジル',)),
    'mongolia': ('モンゴル', ('モンゴル',)), 'iran': ('イラン', ('イラン',)),
    'russia': ('ロシア', ('ロシア',)), 'ukraine': ('ウクライナ', ('ウクライナ',)),
}
THEMES = {
    'elections': ('選挙・政治', ('選挙', '開票', '再選', '民主化', '憲法')),
    'trade': ('貿易', ('貿易', '関税', 'WTO', '輸出', '輸入')),
    'diplomacy': ('外交・国の関係', ('会談', '外交', '国交', '日中', '平和友好', '共同声明')),
    'security': ('安全保障', ('軍', '国防', '防衛', '戦争', '攻撃', '紛争')),
    'transport': ('交通・事故', ('列車', '鉄道', '追突', '衝突', '事故')),
    'economy': ('経済', ('利益', '決算', '株', '金融', '物価', 'エネ高')),
    'other': ('その他', ()),
}


def classify(title):
    countries = [key for key, (_, words) in COUNTRIES.items() if any(word in title for word in words)]
    themes = [key for key, (_, words) in THEMES.items() if words and any(word in title for word in words)]
    return countries, themes or ['other']


def connect(db_path=None):
    path = Path(db_path or os.environ.get('NEWS_ARCHIVE_DB', Path(__file__).parent / 'instance/news_archive.db'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript('''CREATE TABLE IF NOT EXISTS archive_articles (
        url TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
        source TEXT NOT NULL, published_at TEXT, first_seen TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS archive_tags (
        url TEXT NOT NULL, kind TEXT NOT NULL, tag TEXT NOT NULL,
        PRIMARY KEY(url,kind,tag));
        CREATE INDEX IF NOT EXISTS archive_tag_lookup ON archive_tags(kind,tag,url);''')
    if 'image' not in {row['name'] for row in db.execute('PRAGMA table_info(archive_articles)')}:
        db.execute('ALTER TABLE archive_articles ADD COLUMN image TEXT')
    return db


def archive_articles(articles, captured_at=None, db_path=None, update=True, preserve_first_seen=False):
    stamp = captured_at or datetime.now(timezone.utc).isoformat()
    count = 0
    with closing(connect(db_path)) as db, db:
        for item in articles:
            url, title = item.get('url') or '', item.get('title') or ''
            if item.get('reference') or not title or not url.startswith(('https://', 'http://')):
                continue
            source = item.get('source') or '不明'
            if isinstance(source, dict):
                source = source.get('name') or '不明'
            description = item.get('source_description') or item.get('description') or ''
            image = item.get('image') or item.get('urlToImage') or None
            conflict = 'DO UPDATE SET title=excluded.title,description=excluded.description,source=excluded.source,published_at=COALESCE(excluded.published_at,archive_articles.published_at),image=COALESCE(excluded.image,archive_articles.image)' if update else 'DO NOTHING'
            cursor = db.execute('INSERT INTO archive_articles(url,title,description,source,published_at,first_seen,image) VALUES(?,?,?,?,?,?,?) ON CONFLICT(url) ' + conflict,
                (url, title, description, source, item.get('publishedAt') or item.get('published_at'),
                 item.get('first_seen', stamp) if preserve_first_seen else stamp, image))
            if not cursor.rowcount:
                continue
            db.execute('DELETE FROM archive_tags WHERE url=?', (url,))
            countries, themes = classify(title)
            db.executemany('INSERT INTO archive_tags VALUES(?,?,?)',
                [(url, kind, tag) for kind, tags in [('country', countries), ('theme', themes)] for tag in tags])
            count += 1
    return count


def seed_archive(db_path=None):
    payload = json.loads((Path(__file__).parent / 'data/submission_news.json').read_text(encoding='utf-8'))
    archive_articles(payload['articles'], payload['captured_at'], db_path, update=False)


def read_archive(country='', theme='', db_path=None):
    clauses, args = [], []
    for kind, value in [('country', country), ('theme', theme)]:
        if value:
            clauses.append('EXISTS(SELECT 1 FROM archive_tags t WHERE t.url=a.url AND t.kind=? AND t.tag=?)')
            args.extend([kind, value])
    query = 'SELECT a.* FROM archive_articles a'
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    query += ' ORDER BY COALESCE(published_at,first_seen) DESC,url LIMIT 200'
    with closing(connect(db_path)) as db:
        return [dict(row) for row in db.execute(query, args)]
