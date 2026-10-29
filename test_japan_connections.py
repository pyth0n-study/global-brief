import unittest
from japan_connections import japan_connection, attach_japan_connections


class JapanConnectionTests(unittest.TestCase):
    def test_new_url_uses_country_and_topic(self):
        result = japan_connection({'title': 'ブラジル大統領選の結果', 'url': 'https://example.com/new'})
        self.assertEqual(result['matched_ids'], ['brazil_soy'])
        self.assertTrue(result['sources'])
        self.assertEqual(result['life'], '')

    def test_unrelated_news_does_not_get_country_fact(self):
        self.assertFalse(japan_connection({'title': 'ブラジルのサッカー結果'})['matched'])
        self.assertFalse(japan_connection({'title': '中国でマラソン大会'})['matched'])

    def test_negation_retained_in_original_quote(self):
        text = 'KDDIは障害との関連を否定しました。'
        result = japan_connection({'title': '海外の報道', 'description': text, 'url': 'https://example.com/new'})
        self.assertEqual(result['evidence'], [text])
        self.assertEqual(result['life'], '')

    def test_generated_content_not_used_as_evidence(self):
        self.assertFalse(japan_connection({'title': '海外の話題', 'content': '日本企業KDDIに影響が出る。', 'url': 'https://example.com'})['matched'])

    def test_truncated_input_and_unsafe_link_not_quoted(self):
        self.assertFalse(japan_connection({'description': 'KDDIは', 'url': 'https://example.com'})['evidence'])
        self.assertFalse(japan_connection({'description': 'KDDIが発表した。', 'url': 'javascript:alert(1)'})['evidence'])

    def test_old_cache_is_recomputed_without_mutation(self):
        article = {'title': '未対応の記事', 'japan_connection': {'life': '古い予測'}}
        result = attach_japan_connections([article])[0]
        self.assertEqual(result['japan_connection']['life'], '')
        self.assertEqual(article['japan_connection']['life'], '古い予測')


if __name__ == '__main__':
    unittest.main()
