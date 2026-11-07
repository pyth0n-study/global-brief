import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from wikidata_notes import identified_terms, notes_for_article, refresh, valid_note

NOW = datetime(2026, 11, 8, tzinfo=timezone.utc)


def fixture():
    return dict(qid='Q8333', label='連邦捜査局', description='アメリカ合衆国の警察機関',
                english_label='Federal Bureau of Investigation', revision=123,
                fetched_at=NOW.isoformat())


class WikidataNotesTests(unittest.TestCase):
    def test_identity_and_unknown_names(self):
        self.assertEqual([q for _, _, q in identified_terms('メーガン妃の父親をFBIが逮捕 報道')], ['Q3304418', 'Q8333'])
        for title in ['メーガンが会見', 'NOTFBIが会見', '別の出来事(FBIニュース)', 'FBIという同名ドラマ', '映画FBIの新作']:
            self.assertEqual(identified_terms(title), [])

    def test_validation_rejects_wrong_missing_stale_and_forged_link(self):
        n = fixture()
        self.assertIsNotNone(valid_note('Q8333', n, NOW))
        for change in [dict(qid='Q1'), dict(english_label='FBI (TV series)'), dict(description=''),
                       dict(description='<script>bad</script>'), dict(description='曖昧さ回避ページ'),
                       dict(revision=None), dict(fetched_at=(NOW-timedelta(days=8)).isoformat()),
                       dict(fetched_at=(NOW+timedelta(days=1)).isoformat())]:
            self.assertIsNone(valid_note('Q8333', dict(n, **change), NOW))
        note = valid_note('Q8333', dict(n, url='https://evil.example/'), NOW)
        self.assertEqual(note['url'], 'https://www.wikidata.org/w/index.php?title=Q8333&oldid=123')

    def test_refresh_batch_cache_and_no_retries(self):
        session = Mock()
        session.get.return_value.json.return_value = {'entities': {'Q8333': {
            'id': 'Q8333', 'lastrevid': 123,
            'labels': {'en': {'value': 'Federal Bureau of Investigation'}, 'ja': {'value': '連邦捜査局'}},
            'descriptions': {'ja': {'value': 'アメリカ合衆国の警察機関'}}}}}
        payload = {'articles': [{'title': 'FBIが発表'}], 'wikidata': {'entries': {}}}
        self.assertEqual(refresh(payload, session, NOW), 1)
        self.assertEqual(refresh(payload, session, NOW), 0)
        self.assertEqual(session.get.call_count, 1)
        self.assertEqual(session.get.call_args.kwargs['params']['maxlag'], 5)
        session.get.return_value.json.return_value = {'error': {'code': 'maxlag'}}
        self.assertEqual(refresh(payload, session, NOW+timedelta(days=8)), 0)
        self.assertEqual(notes_for_article({'title': 'FBIが発表'}, payload['wikidata'], NOW+timedelta(days=8)), [])

    def test_redirect_and_missing_japanese_hidden(self):
        session = Mock()
        session.get.return_value.json.return_value = {'entities': {'Q8333': {'id': 'Q1', 'labels': {}}}}
        payload = {'articles': [{'title': 'FBIが発表'}], 'wikidata': {'entries': {}}}
        self.assertEqual(refresh(payload, session, NOW), 0)

    def test_reading_never_requests_external_data(self):
        with patch('requests.get', side_effect=AssertionError('External call')):
            notes = notes_for_article({'title': 'FBIが発表'}, {'entries': {'Q8333': fixture()}}, NOW)
        self.assertEqual(notes[0]['term'], 'FBI')

    def test_snapshot_preserves_knowledge_metadata(self):
        from archive_store import export_snapshot, restore_snapshot
        with TemporaryDirectory(dir=Path.cwd()) as folder:
            db = str(Path(folder)/'archive.db')
            payload = {'version': 1, 'articles': [], 'wikidata': {'entries': {'Q8333': fixture()}}}
            restore_snapshot(payload, db)
            saved = export_snapshot(Path(folder)/'archive.json', db, payload)
            self.assertEqual(saved['wikidata'], payload['wikidata'])
