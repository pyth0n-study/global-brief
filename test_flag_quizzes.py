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
  self.assertIsNone(flag_quiz('UNKNOWN'))
  for name,code,*_ in __import__('article_presentation').COUNTRIES:
   q=flag_quiz(code)
   self.assertIsNotNone(q,code)
   self.assertEqual(q['options'][q['answer']],name)
   self.assertEqual(len(set(q['options'])),3)
   self.assertNotIn(name,q['flag_svg'])
   self.assertNotIn('<script',q['flag_svg'])
   self.assertTrue(q['url'].startswith('https://'))

 def test_svg_ids_are_unique_and_external_content_is_rejected(self):
  import xml.etree.ElementTree as ET
  from flag_quizzes import validated_svg
  first,second=flag_quiz('USA'),flag_quiz('USA')
  ids=lambda q:{e.get('id') for e in ET.fromstring(q['flag_svg']).iter() if e.get('id')}
  self.assertFalse(ids(first)&ids(second))
  for raw in ['<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>',
              '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
              '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><use xlink:href="https://example.org/x"/></svg>']:
   validated_svg.cache_clear()
   with patch('pathlib.Path.read_text',return_value=raw):
    self.assertIsNone(validated_svg('USA'))
  validated_svg.cache_clear()
 def test_missing_flag_keeps_map(self):
  feed={'captured_at':'2026-11-08','articles':[dict(title='北朝鮮の報道',description='',image='',url='https://example.org/test')]}
  with patch('submission.load_home_feed',return_value=feed),patch('flag_quizzes.validated_svg',return_value=None),patch('secrets.randbelow',return_value=0):
   page=self.module.app.test_client().get('/').get_data(as_text=True)
  self.assertIn('data-config=',page)
  self.assertNotIn('class="flag-art"',page)

if __name__=='__main__':unittest.main()
