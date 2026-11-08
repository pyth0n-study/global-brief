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
        self.assertEqual(quiz_for_article({'title': 'ソマリアでの出来事'})['code'], 'SOM')
        for title in ('マリーナのニュース', 'マリオの新作'):
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
        self.assertIn('不正選挙論が広がる公園', svg)
        self.assertNotIn('data-country', svg)


class FallbackTests(unittest.TestCase):
    def test_explicit_abbreviations_and_new_countries(self):
        for title, code in [('露統計局にサイバー攻撃', 'RUS'), ('印首都のIT産業', 'IND'), ('英首相が演説', 'GBR'), ('フィリピン当局が発表', 'PHL'), ('エクアドルで豪雨', 'ECU')]:
            self.assertEqual(quiz_for_article({'title': title})['code'], code)
        self.assertEqual(quiz_for_article({'title': 'インドネシアの報道'})['code'], 'IDN')
        for title in ['ガラパゴスで豪雨', '香港の医療', 'トランプ氏が演説']:
            self.assertIsNone(quiz_for_article({'title': title}))

    def test_term_quiz_priority_and_headline_only(self):
        from term_quizzes import term_quiz_for_article
        self.assertEqual(prepare_article({'title': 'OPECプラス生産枠維持'})['term_quiz']['term'], 'OPEC')
        self.assertIsNone(prepare_article({'title': '中国とWTO'})['term_quiz'])
        self.assertIsNone(term_quiz_for_article({'title': '発表(国連通信)', 'description': 'OPECの説明'}))
        self.assertIsNone(term_quiz_for_article({'title': 'NOTWTOの発表'}))
        for title in ['WTOの会合', '国連の会合']:
            self.assertIsNotNone(term_quiz_for_article({'title': title}))

    def test_headline_card_escapes_source(self):
        from preview_visuals import fallback_visual
        svg, label = fallback_visual({'title': '<script>出来事</script>'})
        self.assertNotIn('<script>', svg)
        self.assertIn('&lt;script&gt;', svg)
        self.assertIn('見出し', label)

    def test_all_map_targets_exist(self):
        from article_presentation import COUNTRIES
        from preview_visuals import world_paths
        codes = {c['code'] for c in world_paths()}
        for row in COUNTRIES:
            self.assertIn(row[1], codes)


class ExpandedQuizTests(unittest.TestCase):
    def test_acronyms_and_full_width(self):
        from term_quizzes import term_quiz_for_article
        for title, term in [('APEC首脳会談へ調整', 'APEC'), ('ＡＰＥＣの会合', 'APEC'), ('G7外相会合に出席へ', 'G7'), ('G20首脳会合', 'G20'), ('ASEANの会合', 'ASEAN'), ('WHOが発表', 'WHO'), ('NATOの方針', 'NATO'), ('IMFの融資', 'IMF'), ('EUの政策', 'EU')]:
            q = term_quiz_for_article({'title': title})
            self.assertEqual(q['term'], term)
            self.assertTrue(q['url'].startswith('https://'))
            self.assertEqual(len(set(q['options'])), 3)
            self.assertTrue(0 <= q['answer'] < 3)
        for title in ['APECX社の発表', 'G70の会合', 'G7スマートフォン', '発表(APECニュース)', 'who is the winner']:
            self.assertIsNone(term_quiz_for_article({'title': title}))

    def test_added_maps_do_not_match_parts_of_other_words(self):
        for title, code in [('ケニアで裁判', 'KEN'), ('ソマリアの海賊問題', 'SOM'), ('南米チリで事故', 'CHL'), ('パプアニューギニアの代表処', 'PNG'), ('タイで会合', 'THA')]:
            self.assertEqual(quiz_for_article({'title': title})['code'], code)
        for title in ['タイヤが直撃', 'チリソースの発売', 'マリーナのニュース']:
            self.assertIsNone(quiz_for_article({'title': title}))

    def test_new_map_pins_are_in_their_country_polygons(self):
        import re
        from article_presentation import COUNTRIES
        from preview_visuals import world_paths
        paths = {c['code']: c['path'] for c in world_paths()}
        def contains(code, p):
            x, y = p
            for ring in re.findall(r'M([^M]+)', paths[code]):
                pts = [tuple(map(float, m)) for m in re.findall(r'(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)', ring)]
                hits = 0
                for (ax, ay), (bx, by) in zip(pts, pts[1:]+pts[:1]):
                    if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax: hits += 1
                if hits % 2: return True
            return False
        for _, code, _, _, region, pins in COUNTRIES[24:]:
            self.assertTrue(contains(code, pins[1]), code)
            x,y,w,h = map(float, region.split())
            self.assertTrue(all(x <= px <= x+w and y <= py <= y+h for px,py in pins), code)
