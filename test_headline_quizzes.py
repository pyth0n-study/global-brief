import unittest
from headline_quizzes import headline_quiz_for_article, clean_headline
from article_presentation import prepare_article


class HeadlineQuizTests(unittest.TestCase):
    def test_exact_evidence_and_stable_choices(self):
        a = {'title': 'メーガン妃の父親をFBIが逮捕 報道', 'url': 'https://example.com/story'}
        q = headline_quiz_for_article(a)
        self.assertEqual(q['options'][q['answer']], 'FBI')
        self.assertEqual(q['question'].replace('［　？　］', 'FBI'), a['title'])
        self.assertEqual(q['evidence'], a['title'])
        self.assertEqual(q, headline_quiz_for_article(a))
        self.assertEqual(len(set(q['options'])), 3)
        for choice in q['options']:
            if choice != 'FBI': self.assertNotIn(choice, a['title'])

    def test_reject_ambiguous_partial_and_unusable(self):
        for title in ['FBIとFBIの発表に関する報道', 'NOTFBIの報道について',
                      'FBIではない組織が発表 報道', 'FBIが発表…続きは記事で',
                      'FBIが発表したのか？新たな報道', '今日の歴史（11月7日）',
                      'パリティに関する新たな報道', '気になる新たな出来事について']:
            self.assertIsNone(headline_quiz_for_article({'title': title}), title)

    def test_publisher_not_used_and_no_external_knowledge(self):
        self.assertEqual(clean_headline('新たな出来事について(テレビ朝日系（ANN）)'), '新たな出来事について')
        self.assertIsNone(headline_quiz_for_article({'title': '新たな出来事について(FBIニュース)', 'description': 'FBIが発表'}))
        q = headline_quiz_for_article({'title': '欧州で爆破予告相次ぐ 今度は放送局'})
        self.assertEqual(q['options'][q['answer']], '欧州')
        self.assertNotIn('国', q['explanation'])

    def test_existing_quizzes_take_priority_and_image_failure_has_fallback(self):
        for title in ['韓国で放送局に関する新たな報道', 'OPECプラスの新たな会合']:
            item = prepare_article({'title': title})
            self.assertFalse((item['term_quiz'] or {}).get('kind') == 'headline')
        item = prepare_article({'title': 'メーガン妃の父親をFBIが逮捕 報道', 'image': 'https://example.com/image.jpg'})
        self.assertEqual(item['term_quiz']['kind'], 'headline')
