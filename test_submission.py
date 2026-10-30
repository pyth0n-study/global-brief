import importlib
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


class SubmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        connect = sqlite3.connect
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            with patch.dict(os.environ, {'GEMINI_API_KEY': '', 'ENABLE_LEGACY_APP': '', 'ENABLE_DEBUG_ROUTES': ''}), patch('sqlite3.connect', side_effect=lambda _: connect(str(Path(folder) / 'test.db'))):
                cls.module = importlib.import_module('app')

    def test_pages_render_without_api_calls(self):
        with patch('requests.get', side_effect=AssertionError('External request')), patch.object(self.module, 'summarize_batch', side_effect=AssertionError('AI request')):
            client = self.module.app.test_client()
            for route in ('/', '/play', '/about', '/articles'):
                response = client.get(route)
                self.assertEqual(response.status_code, 200)
            page = client.get('/').get_data(as_text=True)
            self.assertEqual(page.count('<article '), 12)
            self.assertIn('2026-10-29', page)
            self.assertNotIn('data-kind="relations"', page)
            self.assertNotIn('このプレビューでは未作成です', page)
            self.assertNotIn('amd-img/default.jpg', page)
            self.assertIn('data-kind="background"', page)
            self.assertIn('一覧で読む', page)
            self.assertIn('href="/background"', page)
            self.assertIn('ResizeObserver', page)
            self.assertIn('class="headline-toggle"', page)
            self.assertIn('続きを読む⌄', page)
            self.assertNotIn('<button type="button" data-kind="description"', page)
            listing = client.get('/articles').get_data(as_text=True)
            self.assertIn('縦型で読む', listing)
            self.assertEqual(listing.count('class="card"'), 12)
            self.assertIn('sidebar-content', listing)
            self.assertNotIn('onclick="toggleComments(', listing)

    def test_debug_and_legacy_routes_are_closed(self):
        client = self.module.app.test_client()
        for route in ('/debug-summary', '/debug-news', '/legacy'):
            self.assertEqual(client.get(route).status_code, 404)
        self.assertEqual(client.post('/api/comment', json={}).status_code, 404)

    def test_about_returns_to_originating_view(self):
        client = self.module.app.test_client()
        listing = client.get('/articles').get_data(as_text=True)
        self.assertIn('/about?from=list', listing)
        self.assertIn('href="/articles">記事一覧に戻る', client.get('/about?from=list').get_data(as_text=True))
        self.assertIn('href="/">ニュースに戻る', client.get('/about').get_data(as_text=True))

    def test_separated_feed_preview_keeps_interactions(self):
        client = self.module.app.test_client()
        page = client.get('/preview/feed').get_data(as_text=True)
        self.assertIn('separated_feed.css', page)
        self.assertIn('headline-toggle', page)
        self.assertIn('inline-quiz', page)
        self.assertEqual(page.count('<article '), 12)
        for route in ('/', '/play'):
            homepage = client.get(route).get_data(as_text=True)
            self.assertIn('separated_feed.css', homepage)
            self.assertIn('headline-toggle', homepage)
            self.assertIn('inline-quiz', homepage)
            self.assertIn('href="/" aria-label="Global Brief ホーム"', homepage)
