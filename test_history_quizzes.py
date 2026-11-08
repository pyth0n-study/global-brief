import unittest
from history_quizzes import history_quiz_for_article
from article_presentation import prepare_article

TEXT='1965年：南ベトナムのグエン・カオ・キ首相が来韓1991年：盧泰愚大統領が朝鮮半島の非核化を宣言1995年：国連安全保障理事会の非常任理事国に初選出2001年：大統領が会談の'
ARTICLE=dict(title='今日の歴史（11月8日）(聯合ニュース)',description=TEXT,url='https://example.org/history',image='')
class HistoryTests(unittest.TestCase):
 def test_bounded_completed_events_only(self):
  q=history_quiz_for_article(ARTICLE)
  self.assertIsNotNone(q)
  self.assertEqual(set(q['options']),{'1965年','1991年','1995年'})
  self.assertIn(q['options'][q['answer']],q['evidence'])
  self.assertIn(q['evidence'],TEXT)
  self.assertNotIn('2001',q['question'])
  self.assertRegex(q['question'],r'(首相|大統領)が')
  self.assertEqual(q,history_quiz_for_article(ARTICLE))
 def test_unfinished_ambiguous_future_and_unstructured_hidden(self):
  for text in [TEXT.replace('初選出','会議に出'),TEXT.replace('初選出','選出された見込み'),TEXT.replace('1995年','2995年'),TEXT.replace('1995年','1991年'),TEXT.replace('初選出','選出。別の事実を発表'), '説明：'+TEXT, TEXT.replace('来韓','来韓<script>')]:
   self.assertIsNone(history_quiz_for_article(dict(ARTICLE,description=text)),text)
  self.assertIsNone(history_quiz_for_article(dict(ARTICLE,title='今日の国際ニュース')))
  self.assertIsNone(history_quiz_for_article(dict(ARTICLE,url='javascript:alert(1)')))
 def test_same_event_at_multiple_years_hidden(self):
  text='1965年：首相がその国に来韓1991年：首相がその国に来韓1995年：首相がその国に来韓'
  self.assertIsNone(history_quiz_for_article(dict(ARTICLE,description=text)))
 def test_integration_does_not_change_source_or_photo(self):
  a=dict(ARTICLE,image='https://example.org/photo.jpg')
  item=prepare_article(a)
  self.assertEqual(item['term_quiz']['kind'],'history')
  self.assertEqual(item['description'],TEXT)
  self.assertEqual(item['image'],a['image'])

if __name__=='__main__':unittest.main()
