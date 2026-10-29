"""Offline provider contract tests; never call a real news or AI API."""
import unittest
from unittest.mock import Mock, patch
import requests
from news_sources import fetch_articles, NewsSourceError


def response(data):
    return Mock(json=Mock(return_value=data))


class NewsSourcesTests(unittest.TestCase):
    @patch('news_sources.requests.get')
    def test_newsdata_pages_normalize_and_deduplicate(self, get):
        item = {'title': '世界の経済', 'description': None,
                'link': 'https://example.com/1', 'source_name': 'Example',
                'image_url': 'https://example.com/photo.jpg'}
        get.side_effect = [
            response({'status': 'success', 'results': [item], 'nextPage': 'abc'}),
            response({'status': 'success', 'results': [item, dict(item, link='https://example.com/2')]}),
        ]
        articles = fetch_articles('newsdata', newsdata_key='test-secret')
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]['description'], '')
        self.assertEqual(articles[0]['source'], {'name': 'Example'})
        self.assertIsNone(articles[0]['urlToImage'])
        self.assertEqual(get.call_args.kwargs['params']['page'], 'abc')
        self.assertEqual(get.call_args.kwargs['params']['category'], 'world')
        self.assertNotIn('apikey', get.call_args.kwargs['params'])
        self.assertEqual(get.call_count, 2)

    @patch('news_sources.requests.get')
    def test_failed_second_page_does_not_replace_cache_with_partial_data(self, get):
        get.side_effect = [response({'status': 'success', 'results': [{'link': 'https://example.com'}], 'nextPage': 'abc'}), requests.Timeout()]
        with self.assertRaises(requests.Timeout):
            fetch_articles('newsdata', newsdata_key='key')

    @patch('news_sources.requests.get')
    def test_errors_and_missing_keys_do_not_fall_back(self, get):
        for provider in ('newsdata', 'newsapi', 'typo'):
            with self.assertRaises(NewsSourceError):
                fetch_articles(provider)
        get.assert_not_called()
        get.return_value = response({'status': 'error', 'results': {'message': 'bad key'}})
        with self.assertRaises(NewsSourceError):
            fetch_articles('newsdata', newsdata_key='key')

    @patch('news_sources.requests.get')
    def test_newsapi_contract_remains_supported(self, get):
        get.return_value = response({'status': 'ok', 'articles': [{'title': '記事'}]})
        self.assertEqual(fetch_articles('newsapi', newsapi_key='key'), [{'title': '記事'}])


if __name__ == '__main__':
    unittest.main()
