import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import requests

import archive_store as store
from news_archive import archive_articles, read_archive


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        self.db = self.path / 'source.db'
        self.row = dict(title='ロシアとウクライナの戦争', description='説明です。', source='配信元', url='https://example.com/1')

    def test_backup_restores_all_rows_and_first_seen_after_database_loss(self):
        archive_articles([dict(self.row, url=f'https://example.com/{i}') for i in range(205)], '2026-10-29', self.db)
        snapshot = store.export_snapshot(self.path / 'archive.json', self.db)
        self.assertEqual(snapshot['count'], 205)  # UI's 200 limit never truncates storage.
        store.backup_snapshot(self.path / 'archive.json')
        content = (self.path / 'archive-backup.json.gz').read_bytes()
        checksum = (self.path / 'archive-backup.json.gz.sha256').read_text().split()[0]
        self.assertEqual(hashlib.sha256(content).hexdigest(), checksum)
        restored = self.path / 'new.db'
        self.assertEqual(store.restore_snapshot(json.loads(gzip.decompress(content)), restored), 205)
        self.assertEqual(len(read_archive(db_path=restored)), 200)
        self.assertTrue(all(row['first_seen'] == '2026-10-29' for row in read_archive(db_path=restored)))
        store.restore_snapshot(snapshot, restored)
        self.assertEqual(store.export_snapshot(self.path / 'again.json', restored)['count'], 205)

    def test_invalid_snapshot_does_not_partially_import(self):
        archive_articles([self.row], db_path=self.db)
        payload = store.export_snapshot(self.path / 'archive.json', self.db)
        payload['articles'].append({'title': 'invalid'})
        with self.assertRaises(ValueError):
            store.restore_snapshot(payload, self.db)
        self.assertEqual(len(read_archive(db_path=self.db)), 1)

    def test_remote_sync_is_cached_and_failure_keeps_records(self):
        archive_articles([self.row], db_path=self.db)
        payload = store.export_snapshot(self.path / 'archive.json', self.db)
        response = Mock()
        response.json.return_value = payload
        with patch.dict(os.environ, {'NEWS_ARCHIVE_DB': str(self.db), 'NEWS_ARCHIVE_SNAPSHOT_URL': 'https://example.com/archive.json'}), patch.object(store, '_next_check', 0), patch.object(store.requests, 'get', return_value=response) as get:
            self.assertEqual(store.sync_public_archive()['count'], 1)
            store.sync_public_archive()
            self.assertEqual(get.call_count, 1)
            store._next_check = 0
            get.side_effect = requests.Timeout()
            self.assertTrue(store.sync_public_archive()['unavailable'])
            self.assertEqual(len(read_archive(db_path=self.db)), 1)

    def test_failed_fetch_does_not_replace_published_snapshot(self):
        from archive_pipeline import run
        archive_articles([self.row], db_path=self.db)
        path = self.path / 'archive.json'
        store.export_snapshot(path, self.db)
        before = path.read_bytes()
        with patch.dict(os.environ, {'NEWS_ARCHIVE_DB': str(self.db)}), patch('archive_pipeline.fetch_articles', side_effect=requests.Timeout()):
            with self.assertRaises(requests.Timeout):
                run(self.path, fetch=True)
        self.assertEqual(path.read_bytes(), before)
