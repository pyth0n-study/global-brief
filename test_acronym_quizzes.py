from copy import deepcopy
import unittest
from unittest.mock import Mock, patch
from test_wikidata_discovery import NOW, response
from wikidata_discovery import candidates, discover, expanded_name
from wikidata_notes import notes_for_article
from acronym_quizzes import acronym_quiz_for_article

ARTICLE={'title':'IAEAが報告書を公表','description':'国際原子力機関（IAEA）が報告書を公表した。'}
FORMAL='国際原子力機関'
def body():
 return {'entities':{'Q41984':{'id':'Q41984','lastrevid':123,'labels':{'ja':{'value':FORMAL}},'aliases':{'ja':[{'value':'IAEA'}]},'descriptions':{'ja':{'value':'国連の保護下にある自治機関'}},'claims':{'P31':[{'mainsnak':{'datavalue':{'value':{'id':'Q43229'}}}}]}}}}

class AutomaticAcronymTests(unittest.TestCase):
 def resolve(self,article=None,entity=None,search=None):
  p={'articles':[article or ARTICLE],'wikidata':{'entries':{}}}
  s=Mock();s.get.side_effect=[response(search or {'search':[{'id':'Q41984','match':{'text':FORMAL}}]}),response(entity or body())]
  count=discover(p,s,NOW)
  return p,s,count
 def test_unknown_acronym_uses_formal_name_and_creates_sourced_quiz(self):
  p,s,count=self.resolve()
  self.assertEqual(count,1)
  self.assertEqual(s.get.call_args_list[0].kwargs['params']['search'],FORMAL)
  notes=notes_for_article(ARTICLE,p['wikidata'],NOW)
  q=acronym_quiz_for_article(ARTICLE,notes)
  self.assertEqual(q['options'][q['answer']],FORMAL)
  self.assertIn('oldid=123',q['url'])
  self.assertEqual(q,acronym_quiz_for_article(ARTICLE,notes))
  self.assertEqual(discover(p,s,NOW),0)
  self.assertEqual(s.get.call_count,2)
 def test_no_formal_pair_means_no_lookup_or_reuse(self):
  p,s,count=self.resolve()
  for article in [{'title':'IAEAが報告','description':''},{'title':'IAEAが報告','description':'別の機関（IAEA）が報告。'}]:
   self.assertEqual(notes_for_article(article,p['wikidata'],NOW),[])
  p,s,count=self.resolve({'title':'IAEAが報告'})
  self.assertEqual(count,0);s.get.assert_not_called()
 def test_fullwidth_and_reverse_pair(self):
  a={'title':'ＩＡＥＡ（国際原子力機関）が報告'}
  self.assertIn(('IAEA','acronym'),candidates(a))
  self.assertEqual(expanded_name('IAEA',a),FORMAL)
 def test_ambiguous_or_paginated_results_hidden(self):
  hit={'id':'Q41984','match':{'text':FORMAL}}
  for search in [{'search':[hit,hit]},{'search':[hit],'search-continue':10}]:
   p,s,count=self.resolve(search=search)
   self.assertEqual(count,0)
 def test_wrong_alias_missing_description_and_human_hidden(self):
  for case in ['alias','description','human','formal']:
   b=body();e=b['entities']['Q41984']
   if case=='alias':e['aliases']={}
   if case=='description':e['descriptions']={}
   if case=='formal':e['labels']['ja']['value']='別の機関'
   if case=='human':e['claims']['P31'][0]['mainsnak']['datavalue']['value']['id']='Q5'
   self.assertEqual(self.resolve(entity=b)[2],0)
 def test_invalid_or_unattested_notes_cannot_create_question(self):
  self.assertIsNone(acronym_quiz_for_article(ARTICLE,[{'identity':{'kind':'acronym'}}]))
  self.assertIsNone(acronym_quiz_for_article(ARTICLE,[{'identity':{'kind':'acronym','term':'IAEA','formal_name':'別の正式名称'}}]))
 def test_card_uses_cached_question_without_network(self):
  from article_presentation import prepare_article
  p,_,_=self.resolve()
  notes=notes_for_article(ARTICLE,p['wikidata'],NOW)
  with patch('wikidata_notes.notes_for_article',return_value=notes), patch('requests.get',side_effect=AssertionError('Network')):
   item=prepare_article(dict(ARTICLE,url='https://example.org/test'))
  self.assertEqual(item['term_quiz']['kind'],'acronym')
  self.assertEqual(item['knowledge_notes'],[])

if __name__=='__main__':unittest.main()
