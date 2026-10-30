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
        self.assertEqual(usable_image('https://image.news.livedoor.com/newsimage/stf/o/g/ogp_image_32679556_3f268f2d07b5.jpg'), '')
        other = 'https://image.news.livedoor.com/newsimage/stf/o/g/ogp_image_other.jpg'
        self.assertEqual(usable_image(other), other)
        self.assertEqual(usable_image('https://example.com/photo.jpg'), 'https://example.com/photo.jpg')

    def test_election_has_country_quiz_without_ai(self):
        self.assertEqual(quiz_for_article({'title': '米中間選挙 エネ高で揺らぐ共和地盤'})['code'], 'USA')
        self.assertEqual(quiz_for_article({'title': 'イスラエル、85％開票で首相陣営53議席'})['code'], 'ISR')

    def test_unknown_country_is_not_guessed_from_dateline(self):
        self.assertIsNone(quiz_for_article({'title': 'サメの映像', 'description': '【パリ共同】'}))

    def test_missing_image_articles_have_explicit_country_quizzes(self):
        self.assertEqual(quiz_for_article({'title': '北朝鮮、無人機と放射砲で示威'})['code'], 'PRK')
        self.assertEqual(quiz_for_article({'title': 'マリで発見の火星隕石 水の存在示唆'})['code'], 'MLI')
        for title in ('ソマリアでの出来事', 'マリーナのニュース', 'マリオの新作'):
            self.assertIsNone(quiz_for_article({'title': title}))

    def test_original_is_retained(self):
        item = prepare_article(dict(title='スペイン列車事故(共同通信)', image=''))
        self.assertEqual(item['title'], 'スペイン列車事故(共同通信)')
        self.assertEqual(item['display_title'], 'スペイン列車事故')

    def test_publisher_language_does_not_select_japan(self):
        self.assertIsNone(quiz_for_article({'title': 'ハイネケン、ビール販売に悪影響(中央日報日本語版)'}))
        self.assertEqual(quiz_for_article({'title': '韓国の選挙(中央日報日本語版)'})['code'], 'KOR')

    def test_theme_visual_never_infers_a_country(self):
        from preview_visuals import fallback_visual
        svg, _ = fallback_visual({'title': 'ハイネケンの発表(中央日報日本語版)', 'description': '英国のパブへの資料。'})
        self.assertNotIn('日本', svg)
        self.assertNotIn('英国', svg)
        svg, _ = fallback_visual({'title': '不正選挙論が広がる公園', 'description': ''})
        self.assertIn('主張と確認された事実を分けて読む', svg)
        self.assertNotIn('data-country', svg)
