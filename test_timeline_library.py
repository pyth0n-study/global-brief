import unittest
from timeline_library import load_timelines, timeline_for_article, attach_timelines


class TimelineLibraryTests(unittest.TestCase):
    def test_requires_country_and_topic(self):
        self.assertIsNone(timeline_for_article({'title': 'ブラジルで洪水'}))
        self.assertIsNone(timeline_for_article({'title': '中国のマラソン大会'}))
        self.assertIsNone(timeline_for_article({'title': '大統領選の結果'}))

    def test_matches_three_reviewed_topics(self):
        for headline, key in [('ブラジル大統領選', 'brazil_elections'),
                              ('中国の輸出規制', 'china_trade'),
                              ('日中首脳会談', 'japan_china_diplomacy')]:
            self.assertEqual(timeline_for_article({'title': headline}), key)

    def test_library_has_three_sourced_moments_per_topic(self):
        for timeline in load_timelines().values():
            self.assertEqual(len(timeline['moments']), 3)
            self.assertTrue(timeline['reviewed_at'])
            for moment in timeline['moments']:
                self.assertTrue(moment['source'].startswith('https://'))
                self.assertTrue(moment['publisher'])

    def test_new_articles_and_stale_cache_are_reclassified(self):
        articles = [{'title': '中国の貿易交渉', 'timeline_id': 'obsolete'},
                    {'title': 'ブラジルで洪水', 'timeline_id': 'brazil_elections'}]
        result = attach_timelines(articles)
        self.assertEqual(result[0]['timeline_id'], 'china_trade')
        self.assertIsNone(result[1]['timeline'])
        self.assertEqual(articles[0]['timeline_id'], 'obsolete')


if __name__ == '__main__':
    unittest.main()
