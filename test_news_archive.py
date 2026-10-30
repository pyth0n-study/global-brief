import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from news_archive import archive_articles, read_archive, seed_archive
from background_guides import guides_for


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.folder.cleanup)
        self.db = Path(self.folder.name) / 'archive.db'
        self.article = dict(title='日本と中国の首脳会談', description='両国の会談が開かれました。', source={'name': '配信元'}, url='https://example.com/news')

    def test_deduplicates_and_preserves_first_acquired_date(self):
        archive_articles([self.article], '2026-10-29', self.db)
        archive_articles([dict(self.article, description='更新した原文です。')], '2026-10-30', self.db)
        rows = read_archive(db_path=self.db)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['first_seen'], '2026-10-29')
        self.assertEqual(rows[0]['description'], '更新した原文です。')

    def test_country_and_theme_filter_and_durable_reopen(self):
        archive_articles([self.article], '2026-10-29', self.db)
        self.assertEqual(len(read_archive('china', 'diplomacy', self.db)), 1)
        self.assertEqual(len(read_archive('japan', 'diplomacy', self.db)), 1)
        self.assertEqual(read_archive('china', 'elections', self.db), [])
        self.assertEqual(read_archive("' OR 1=1 --", db_path=self.db), [])

    def test_unknown_country_is_not_guessed_from_description(self):
        article = dict(self.article, title='会談が行われた', description='【パリ共同】会談です。')
        archive_articles([article], db_path=self.db)
        self.assertEqual(read_archive('france', db_path=self.db), [])

    def test_seed_is_idempotent_and_excludes_reference_cards(self):
        seed_archive(self.db)
        seed_archive(self.db)
        rows = read_archive(db_path=self.db)
        self.assertEqual(len(rows), 10)
        self.assertFalse(any('背景資料' in a['source'] for a in rows))
        self.assertTrue(all(a['published_at'] is None for a in rows))

    def test_basic_guides_remain_separate(self):
        self.assertEqual(len(guides_for()), 3)
        self.assertEqual(len(guides_for('china', 'trade')), 1)
        self.assertEqual(guides_for('spain'), [])

    def test_background_routes_without_network(self):
        from app import app
        with patch.dict(os.environ, {'NEWS_ARCHIVE_DB': str(self.db)}), patch('requests.get', side_effect=AssertionError('No network')):
            client = app.test_client()
            page = client.get('/background').get_data(as_text=True)
            self.assertIn('基本の背景', page)
            self.assertIn('これまでの記事', page)
            self.assertIn('WTO', page)
            page = client.get('/background?country=spain&theme=transport').get_data(as_text=True)
            self.assertIn('基本解説は、まだありません', page)
            self.assertIn('列車事故', page)
            self.assertEqual(client.get('/background?country=unknown').status_code, 400)

    def test_source_is_archived_before_ai_processing(self):
        import app as module
        with patch.object(module, 'fetch_articles', return_value=[self.article]), patch('news_archive.archive_articles') as save, patch.object(module, 'summarize_batch', side_effect=RuntimeError('AI unavailable')):
            with self.assertRaises(RuntimeError):
                module.fetch_news()
            save.assert_called_once_with([self.article])
