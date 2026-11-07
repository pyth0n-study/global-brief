from copy import deepcopy
from datetime import datetime, timezone
import unittest
from unittest.mock import Mock
import requests

from wikidata_discovery import candidates, context_role, discover, dynamic_matches
from wikidata_notes import notes_for_article, refresh, valid_note

NOW = datetime(2026, 11, 8, tzinfo=timezone.utc)
TERM = 'アントニオ・グテーレス'
ARTICLE = {'title': TERM + '氏が会見', 'description': '国連事務総長の' + TERM + '氏'}


def response(body):
    result = Mock()
    result.json.return_value = body
    return result


def search_body():
    return {'search': [{'id': 'Q311440', 'match': {'text': TERM}}]}


def entity_body():
    return {'entities': {'Q311440': {'id': 'Q311440', 'lastrevid': 123,
        'labels': {'ja': {'value': TERM}, 'en': {'value': 'António Guterres'}},
        'descriptions': {'ja': {'value': '国際連合の事務総長'}},
        'claims': {'P31': [{'mainsnak': {'datavalue': {'value': {'id': 'Q5'}}}}]}}}}


class DiscoveryTests(unittest.TestCase):
    def payload(self):
        return {'articles': [ARTICLE], 'wikidata': {'entries': {}}}

    def test_candidate_scope(self):
        self.assertEqual(candidates(ARTICLE), [(TERM, 'person')])
        self.assertEqual(candidates({'title': '国際移住機関が発表'}), [('国際移住機関', 'organization')])
        for title in ['グテーレス氏が会見', 'ABCが発表', '同名ドラマのアントニオ・グテーレス氏']:
            self.assertEqual(candidates({'title': title}), [])

    def test_exact_full_name_and_role_are_required_and_cached(self):
        session = Mock()
        session.get.side_effect = [response(search_body()), response(entity_body())]
        payload = self.payload()
        self.assertEqual(refresh(payload, session, NOW), 1)
        note = notes_for_article(ARTICLE, payload['wikidata'], NOW)[0]
        self.assertEqual(note['qid'], 'Q311440')
        self.assertIn('oldid=123', note['url'])
        self.assertEqual(refresh(payload, session, NOW), 0)
        self.assertEqual(session.get.call_count, 2)
        self.assertEqual(notes_for_article({'title': TERM+'氏', 'description': ''}, payload['wikidata'], NOW), [])

    def test_wrong_occupation_elsewhere_does_not_count(self):
        article = {'title': 'クリス・ホートン氏', 'description': '記者がアニメーターを取材した。'}
        self.assertIsNone(context_role(article, 'アメリカのアニメーター', 'クリス・ホートン'))
        self.assertIsNone(context_role(ARTICLE, 'アメリカのアニメーター', TERM))

    def test_ambiguous_or_incomplete_search_is_hidden(self):
        for body in [dict(search=[search_body()['search'][0]]*2),
                     dict(search=search_body()['search'], **{'search-continue': 10}),
                     {'search': [{'id': 'Q311440', 'match': {'text': '別名'}}]}]:
            session = Mock()
            session.get.return_value = response(body)
            payload = self.payload()
            self.assertEqual(discover(payload, session, NOW), 0)
            self.assertEqual(payload['wikidata']['entries'], {})
            self.assertEqual(session.get.call_count, 1)

    def test_nonperson_or_missing_description_is_hidden(self):
        for mutation in ['missing_description', 'wrong_type', 'redirect']:
            body = deepcopy(entity_body())
            e = body['entities']['Q311440']
            if mutation == 'missing_description': e['descriptions'] = {}
            elif mutation == 'wrong_type': e['claims'] = {}
            else: e['id'] = 'Q1'
            session = Mock()
            session.get.side_effect = [response(search_body()), response(body)]
            payload = self.payload()
            self.assertEqual(discover(payload, session, NOW), 0)
            self.assertEqual(payload['wikidata']['entries'], {})

    def test_rate_limit_stops_without_retry(self):
        session = Mock()
        session.get.side_effect = requests.HTTPError('429')
        payload = self.payload()
        self.assertEqual(refresh(payload, session, NOW), 0)
        self.assertEqual(refresh(payload, session, NOW), 0)
        self.assertEqual(session.get.call_count, 1)

    def test_search_budget_is_bounded(self):
        session = Mock()
        session.get.return_value = response({'search': []})
        payload = {'articles': [{'title': 'テスト・' + suffix + '氏が会見'}
            for suffix in ['アア', 'イイ', 'ウウ', 'エエ', 'オオ', 'カカ', 'キキ', 'クク']],
            'wikidata': {'entries': {}}}
        discover(payload, session, NOW)
        self.assertEqual(session.get.call_count, 6)
