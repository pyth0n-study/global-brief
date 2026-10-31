from datetime import datetime, timezone
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from watch_points import reserve, generate, validate_watch
from news_archive import archive_articles, read_archive
from archive_store import export_snapshot, restore_snapshot

SENTENCE = '今後は関係する政党の間で連立政権に向けた交渉が続く見通しです。'

def article(i):
    return dict(url=f'https://example.com/{i}',title='選挙後の交渉',description=SENTENCE,source='配信元',first_seen='2026-10-30',published_at='2026-10-30')

class WatchTests(unittest.TestCase):
    def test_reservations_survive_reruns_and_reset_on_jst_date(self):
        payload = dict(articles=[article(i) for i in range(8)])
        now = datetime(2026,10,30,14,59,tzinfo=timezone.utc)
        self.assertEqual(reserve(payload,'first',now),3)
        self.assertEqual(reserve(payload,'rerun',now),0)
        self.assertEqual(reserve(payload,'next-day',now.replace(hour=15)),3)

    def test_requires_exact_complete_forward_looking_evidence(self):
        self.assertIsNotNone(validate_watch(dict(text=SENTENCE,evidence=SENTENCE),SENTENCE))
        for text in ('物価が上がるでしょう。', SENTENCE[:-1], '交渉が続く見通しです。'):
            self.assertIsNone(validate_watch(dict(text=text,evidence=text),SENTENCE))
        self.assertIsNone(validate_watch(dict(text='変更した文',evidence=SENTENCE),SENTENCE))
        self.assertEqual(reserve(dict(articles=[dict(article(1),description='結果を発表しました。')]),'x'),0)

    @patch('watch_points.requests.post')
    def test_quota_stops_without_retry(self, post):
        payload = dict(articles=[article(i) for i in range(4)])
        reserve(payload,'run')
        post.return_value = Mock(status_code=429)
        generate(payload,'run','dummy')
        self.assertEqual(post.call_count,1)
        self.assertFalse(any(a.get('watch_point') for a in payload['articles']))
        self.assertEqual(reserve(payload,'retry'),0)
        generate(payload,'run','dummy')
        self.assertEqual(post.call_count,1)

    @patch('watch_points.requests.post')
    def test_valid_result_and_old_owner_does_not_repeat(self, post):
        import json
        payload = dict(articles=[article(1)])
        reserve(payload,'run')
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value={'candidates':[{'content':{'parts':[{'text':json.dumps({'evidence':SENTENCE})}]}}]}
        generate(payload,'different-owner','dummy')
        post.assert_not_called()
        generate(payload,'run','dummy')
        self.assertEqual(payload['articles'][0]['watch_point']['text'],SENTENCE)
        generate(payload,'run','dummy')
        self.assertEqual(post.call_count,1)

    def test_snapshot_and_fetch_keep_valid_result_but_changed_source_hides_it(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            db=Path(folder)/'source.db'
            row=article(1)
            row['watch_point']=dict(text=SENTENCE,evidence=SENTENCE)
            archive_articles([row],db_path=db)
            payload=export_snapshot(Path(folder)/'archive.json',db,metadata={'watch_trial':{'attempts':[]}})
            self.assertIn('watch_trial',payload)
            other=Path(folder)/'restore.db'
            restore_snapshot(payload,other)
            self.assertIsNotNone(validate_watch(read_archive(db_path=other)[0]['watch_point'],SENTENCE))
            row.pop('watch_point')
            archive_articles([row],db_path=other)
            self.assertIsNotNone(read_archive(db_path=other)[0]['watch_point'])
            archive_articles([dict(row,description='過去の結果のみです。')],db_path=other)
            self.assertIsNone(read_archive(db_path=other)[0]['watch_point'])

    def test_display_hides_unsupported_watch_point(self):
        from article_presentation import prepare_article
        row=article(1)
        row['watch_point']=dict(text=SENTENCE,evidence=SENTENCE)
        self.assertIsNotNone(prepare_article(row)['watch_point'])
        row['watch_point']=dict(text='日本の物価が上昇します。',evidence=SENTENCE)
        self.assertIsNone(prepare_article(row)['watch_point'])

    @patch('watch_points.requests.post')
    def test_missing_key_never_calls_model(self, post):
        payload=dict(articles=[article(1)])
        reserve(payload,'run')
        generate(payload,'run',None)
        post.assert_not_called()
