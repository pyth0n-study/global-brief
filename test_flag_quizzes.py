import unittest
from unittest.mock import patch
from flag_quizzes import flag_quiz
from test_submission import SubmissionTests

class FlagPreviewTests(SubmissionTests):
 def test_flag_preview_and_public_top_random_branches(self):
  feed={'captured_at':'2026-11-08','articles':[dict(title='ポーランドで会合',description='',image='',url='https://example.org/poland')]}
  with patch('submission.load_home_feed',return_value=feed),patch('requests.get',side_effect=AssertionError('Network')):
   c=self.module.app.test_client()
   for coin,kind in [(0,'flag'),(1,'map')]:
    with patch('secrets.randbelow',return_value=coin):
     for route in ['/', '/play', '/preview/flags']:
      r=c.get(route);page=r.get_data(as_text=True)
      self.assertEqual(r.status_code,200)
      self.assertEqual('class="flag-art"' in page,kind=='flag')
      self.assertEqual('data-config=' in page,kind=='map')
   with patch('secrets.randbelow',return_value=1):
    self.assertNotIn('class="flag-art"',c.get('/?quiz=flag').get_data(as_text=True))
   self.assertIn('class="flag-art"',c.get('/preview/flags?quiz=flag').get_data(as_text=True))
 def test_assets_and_answer_mapping(self):
  self.assertIsNone(flag_quiz('PRK'))
  for code,name in [('POL','ポーランド'),('DEU','ドイツ'),('FRA','フランス')]:
   q=flag_quiz(code)
   self.assertEqual(q['options'][q['answer']],name)
   self.assertNotIn(name,q['flag_svg'])
   self.assertNotIn('<script',q['flag_svg'])
   self.assertTrue(q['url'].startswith('https://'))

if __name__=='__main__':unittest.main()
