import unittest
from article_presentation import prepare_article, quiz_for_article, usable_image


class PresentationTests(unittest.TestCase):
    def test_truncated_description_preserves_source(self):
        raw = '現地当局が発表しました。続報によると現地の'
        item = prepare_article(dict(title='スペインの報道', description=raw, image=''))
        self.assertEqual(item['description'], raw)
        self.assertEqual(item['description_excerpt'], '現地当局が発表しました。')
        self.assertTrue(item['description_incomplete'])
        item = prepare_article(dict(title='報道', description='途中で切れた', image=''))
        self.assertEqual(item['description_excerpt'], '')
        self.assertTrue(item['description_incomplete'])

    def test_logo_is_not_a_news_photo(self):
        self.assertEqual(usable_image('https://newsatcl-pctr.c.yimg.jp/t/amd-img/default.jpg?exp=10800'), '')
        self.assertEqual(usable_image('https://example.com/photo.jpg'), 'https://example.com/photo.jpg')

    def test_election_has_country_quiz_without_ai(self):
        self.assertEqual(quiz_for_article({'title': '米中間選挙 エネ高で揺らぐ共和地盤'})['code'], 'USA')
        self.assertEqual(quiz_for_article({'title': 'イスラエル、85％開票で首相陣営53議席'})['code'], 'ISR')

    def test_unknown_country_is_not_guessed_from_dateline(self):
        self.assertIsNone(quiz_for_article({'title': 'サメの映像', 'description': '【パリ共同】'}))

    def test_original_is_retained(self):
        item = prepare_article(dict(title='スペイン列車事故(共同通信)', image=''))
        self.assertEqual(item['title'], 'スペイン列車事故(共同通信)')
        self.assertEqual(item['display_title'], 'スペイン列車事故')
