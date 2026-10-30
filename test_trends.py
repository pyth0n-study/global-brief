"""動向と表示記事の対応を外部APIなしで検証する。"""
import importlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock


class TrendsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as folder:
            connect = sqlite3.connect
            with patch('sqlite3.connect', side_effect=lambda _: connect(str(Path(folder) / 'test.db'))), patch('google.genai.Client'):
                cls.module = importlib.import_module('app')

    def setUp(self):
        self.m = self.module
        client_patch = patch.object(self.m, 'client', Mock())
        client_patch.start()
        self.addCleanup(client_patch.stop)
        archive_patch = patch('news_archive.archive_articles')
        archive_patch.start()
        self.addCleanup(archive_patch.stop)
        for name in ('cache', 'keyword_cache', 'insight_cache', 'is_world_cache', 'headline_cache', 'focus_cache'):
            getattr(self.m, name).clear()
        self.m.trends_cache = ['前回の動向']
        self.articles = [
            {'title': '各国の経済動向', 'description': '経済に関する報道', 'url': 'https://example.com/1'},
            {'title': '政府が外交方針を発表', 'description': '外交に関する報道', 'url': 'https://example.com/2'},
        ]

    def fetch(self, result, articles=None):
        response = Mock()
        response.json.return_value = {'status': 'ok', 'articles': self.articles if articles is None else articles}
        with patch.object(self.m, 'NEWS_PROVIDER', 'newsapi'), patch.object(self.m.requests, 'get', return_value=response), patch.object(self.m, 'summarize_batch', return_value=result) as batch, patch.object(self.m, 'get_article_image', return_value=(None, None, None)):
            news = self.m.fetch_news()
        return news, batch

    def test_cached_articles_are_included_in_overall_trends(self):
        self.m.cache[self.articles[0]['title']] = '既存の要約'
        news, batch = self.fetch(({0: ('要約1', '', '', True, '世界のお金の動き'), 1: ('要約2', '', '', True, None)}, ['動向1', '動向2', '動向3']))
        self.assertEqual(len(batch.call_args.args[0]), 2)
        self.assertEqual(len(news), 2)
        with self.m.app.test_request_context('/'):
            page = self.m.render_template('index.html', news=news, trends=self.m.trends_cache, error=False)
        self.assertLess(page.index('trends-section'), page.index('class="card"'))
        self.assertEqual(page.count('<li>動向'), 3)

    def test_ai_failure_clears_stale_trends_and_preserves_summary(self):
        self.m.cache[self.articles[0]['title']] = '既存の要約'
        news, _ = self.fetch(({}, []))
        self.assertEqual(self.m.trends_cache, [])
        self.assertEqual(news[0]['content'], '既存の要約')
        with self.m.app.test_request_context('/'):
            page = self.m.render_template('index.html', news=news, trends=[], error=False)
        self.assertIn('今後の動向を生成できませんでした', page)

    def test_no_articles_clears_trends(self):
        news, _ = self.fetch(({}, []), articles=[])
        self.assertEqual(news, [])
        self.assertEqual(self.m.trends_cache, [])

    def test_news_failure_keeps_previous_trends(self):
        with patch.object(self.m.requests, 'get', side_effect=RuntimeError('offline')):
            self.assertIsNone(self.m.fetch_news())
        self.assertEqual(self.m.trends_cache, ['前回の動向'])

    def test_newsdata_skips_missing_descriptions_and_disables_images(self):
        articles = [dict(self.articles[0], description=''), self.articles[1]]
        with patch.object(self.m, 'NEWS_PROVIDER', 'newsdata'), patch.object(self.m, 'fetch_articles', return_value=articles), patch.object(self.m, 'summarize_batch', return_value=({0: ('要約', '', '', True, None)}, ['動向'])) as batch, patch.object(self.m, 'get_article_image') as images:
            news = self.m.fetch_news()
            self.assertEqual(len(news), 1)
            self.assertEqual(len(batch.call_args.args[0]), 1)
            self.assertIsNone(news[0]['image'])
            images.assert_not_called()
            with self.m.app.test_request_context('/'):
                page = self.m.render_template('index.html', news=news, trends=['動向'], error=False)
            self.assertIn('NewsData.io', page)
            self.assertIn('12時間', page)

    def test_newsdata_excludes_domestic_even_in_politics_or_economy(self):
        results = {0: ('国内経済', '', '', False, None), 1: ('外交', '', '', True, None)}
        with patch.object(self.m, 'NEWS_PROVIDER', 'newsdata'), patch.object(self.m, 'fetch_articles', return_value=self.articles), patch.object(self.m, 'summarize_batch', return_value=(results, [])):
            news = self.m.fetch_news()
        self.assertEqual(len(news), 1)
        self.assertEqual(news[0]['title'], self.articles[1]['title'])

    def test_provider_caches_are_isolated_and_restored(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(self.m, 'DATABASE', str(Path(folder) / 'cache.db')):
            self.m.init_db()
            with patch.object(self.m, 'CACHE_STATE_KEY', 'cache'):
                self.m.news_cache = [{'title': '旧取得元'}]
                self.m.save_cache_state()
            with patch.object(self.m, 'CACHE_STATE_KEY', 'cache:newsdata'):
                self.m.news_cache = []
                self.m.load_cache_state()
                self.assertEqual(self.m.news_cache, [])
                self.m.news_cache = [{'title': '新取得元'}]
                self.m.save_cache_state()
                self.m.news_cache = []
                self.m.load_cache_state()
                self.assertEqual(self.m.news_cache, [{'title': '新取得元'}])

    def test_friendly_title_is_generated_in_same_call(self):
        parsed = self.m._BatchResult(articles=[{
            'index': 0, 'skip': False, 'summary': '要約', 'keywords': '',
            'insight': '', 'is_world': True,
            'friendly_title': '  世界のお金は\nどう動いている？  ',
        }], trends=[])
        with patch.object(self.m.client.models, 'generate_content', return_value=Mock(parsed=parsed)) as generate:
            results, _ = self.m.summarize_batch([{'index': 0, 'title': '各国の経済動向', 'content': '経済に関する報道'}])
        generate.assert_called_once()
        self.assertEqual(results[0][4], '世界のお金は どう動いている？')

    def test_focus_is_verified_in_same_summary_call(self):
        sentence = '当局は計画を検討中で、まだ実施は決まっていません。'
        parsed = self.m._BatchResult(articles=[dict(index=0, skip=False, summary='要約', keywords='', insight='', is_world=True, focus_point=sentence, focus_evidence=sentence)], trends=[])
        with patch.object(self.m.client.models, 'generate_content', return_value=Mock(parsed=parsed)) as generate:
            results, _ = self.m.summarize_batch([dict(index=0, title='計画の検討', content=sentence)])
        generate.assert_called_once()
        self.assertEqual(results[0][5]['point'], sentence)
        parsed.articles[0].focus_point = '計画の実施が決まりました。'
        with patch.object(self.m.client.models, 'generate_content', return_value=Mock(parsed=parsed)):
            results, _ = self.m.summarize_batch([dict(index=0, title='計画の検討', content=sentence)])
        self.assertIsNone(results[0][5])

    def test_missing_or_overlong_friendly_title_falls_back(self):
        item = self.m._ArticleResult(index=0, skip=False, summary='要約', keywords='', insight='', is_world=True)
        self.assertIsNone(self.m.normalize_friendly_title(item.friendly_title))
        self.assertIsNone(self.m.normalize_friendly_title('あ' * 61))
        self.assertIsNone(self.m.normalize_friendly_title(' \n '))
        news, _ = self.fetch(({0: ('要約', '', '', True, None)}, []), articles=self.articles[:1])
        # 再起動前の旧形式キャッシュにも対応する。
        news[0].pop('friendly_title')
        with self.m.app.test_request_context('/'):
            page = self.m.render_template('index.html', news=news, trends=[], error=False)
        self.assertIn('<h2>各国の経済動向</h2>', page)
        self.assertNotIn('AIのやさしい見出し', page)

    def test_friendly_title_keeps_original_and_escapes_html(self):
        news, _ = self.fetch(({0: ('要約', '', '', True, '<script>危険</script>')}, []), articles=self.articles[:1])
        with self.m.app.test_request_context('/'):
            page = self.m.render_template('index.html', news=news, trends=[], error=False)
        self.assertNotIn('元の見出し：', page)
        self.assertIn('&lt;script&gt;危険&lt;/script&gt;', page)
        self.assertNotIn('<script>危険</script>', page)
        self.assertIn('data-title="各国の経済動向"', page)

    def test_ai_failure_preserves_existing_friendly_title(self):
        title = self.articles[0]['title']
        self.m.cache[title] = '既存の要約'
        self.m.headline_cache[title] = '世界のお金の動き'
        news, _ = self.fetch(({}, []))
        self.assertEqual(news[0]['friendly_title'], '世界のお金の動き')
        self.assertIsNone(news[1]['friendly_title'])


if __name__ == '__main__':
    unittest.main()
