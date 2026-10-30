import os
from contextlib import closing
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from news_archive import archive_articles, read_archive
from public_feed import load_home_feed


class PublicFeedTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.folder.cleanup)
        self.db = Path(self.folder.name) / 'archive.db'
        env = patch.dict(os.environ, {'NEWS_ARCHIVE_DB': str(self.db)})
        env.start()
        self.addCleanup(env.stop)
        sync = patch('public_feed.sync_public_archive', return_value={'updated_at': '2026-10-30T12:00:00Z'})
        sync.start()
        self.addCleanup(sync.stop)

    def test_latest_twenty_and_image_are_loaded_without_news_or_ai(self):
        rows = [dict(title='ブラジルの選挙', description='結果が発表されました。', source='配信元',
                     url=f'https://example.com/{i}', publishedAt=f'2026-10-30 {i:02}:00:00',
                     urlToImage='https://example.com/photo.jpg' if i == 23 else None) for i in range(24)]
        archive_articles(rows)
        with patch('requests.get', side_effect=AssertionError('No provider call')):
            payload = load_home_feed()
        self.assertTrue(payload['live_archive'])
        self.assertEqual(len(payload['articles']), 20)
        self.assertEqual(payload['articles'][0]['url'], 'https://example.com/23')
        self.assertEqual(payload['articles'][0]['image'], 'https://example.com/photo.jpg')
        from app import app
        with patch('submission.load_home_feed', return_value=payload):
            html = app.test_client().get('/').get_data(as_text=True)
        self.assertIn('https://example.com/photo.jpg', html)
        self.assertIn('class="headline-toggle"', html)
        self.assertIn('inline-quiz', html)
        self.assertIn('data-layout="immersive"', html)
        self.assertNotIn('背景資料 · 新着ニュースではありません', html)

    def test_initial_offline_fallback_keeps_demo(self):
        payload = load_home_feed()
        self.assertFalse(payload['live_archive'])
        self.assertEqual(len(payload['articles']), 12)

    def test_old_database_migrates_and_old_snapshots_preserve_image(self):
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('CREATE TABLE archive_articles(url TEXT PRIMARY KEY,title TEXT NOT NULL,description TEXT NOT NULL,source TEXT NOT NULL,published_at TEXT,first_seen TEXT NOT NULL)')
        row = dict(title='ブラジルのニュース', description='説明です。', source='配信元', url='https://example.com/1')
        archive_articles([dict(row, image='https://example.com/photo.jpg')])
        archive_articles([row])
        self.assertEqual(read_archive()[0]['image'], 'https://example.com/photo.jpg')

    def test_shared_link_opens_old_archived_article_and_missing_link_is_explicit(self):
        import hashlib
        rows = [dict(title='ブラジルの選挙', description='発表されました。', source='配信元', url=f'https://example.com/{i}', publishedAt='2026-10-30') for i in range(205)]
        old = dict(title='ブラジルの過去の記事', description='過去の説明です。', source='配信元', url='https://example.com/old', publishedAt='2020-01-01')
        archive_articles(rows + [old])
        payload = load_home_feed(hashlib.md5(old['url'].encode()).hexdigest())
        self.assertEqual(payload['articles'][0]['url'], old['url'])
        self.assertEqual(len(payload['articles']), 20)
        self.assertTrue(load_home_feed('f' * 32)['requested_not_found'])
        self.assertTrue(load_home_feed('not-an-id')['requested_not_found'])
