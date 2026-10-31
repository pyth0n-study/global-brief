"""Portable archive snapshots; GitHub is durable storage, SQLite is a local read cache."""
from contextlib import closing
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import threading
import time

import requests
from news_archive import archive_articles, connect

SNAPSHOT_URL = 'https://raw.githubusercontent.com/pyth0n-study/global-brief/archive-data/archive.json'
_lock = threading.Lock()
_next_check = 0
_status = {'updated_at': None, 'count': None, 'unavailable': False}


def restore_snapshot(payload, db_path=None):
    if not isinstance(payload, dict) or payload.get('version') != 1 or not isinstance(payload.get('articles'), list):
        raise ValueError('Unsupported archive snapshot')
    rows = payload['articles']
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) for k in ('url', 'title', 'description', 'source', 'first_seen')):
            raise ValueError('Invalid archive row')
        if not row['url'].startswith(('http://', 'https://')) or not row['title'] or not row['first_seen']:
            raise ValueError('Invalid archive article')
        if row.get('published_at') is not None and not isinstance(row['published_at'], str):
            raise ValueError('Invalid publication date')
        if row.get('image') is not None and not isinstance(row['image'], str):
            raise ValueError('Invalid image URL')
    archive_articles(rows, db_path=db_path, preserve_first_seen=True)
    return len(rows)


def export_snapshot(path, db_path=None, metadata=None):
    with closing(connect(db_path)) as db:
        rows = [dict(row) for row in db.execute('SELECT * FROM archive_articles ORDER BY first_seen,url')]
    from watch_points import validate_watch
    for row in rows:
        row['watch_point'] = validate_watch(row.get('watch_point'), row['description'])
    payload = dict(version=1, updated_at=datetime.now(timezone.utc).isoformat(), count=len(rows), articles=rows)
    if metadata and isinstance(metadata.get('watch_trial'), dict):
        payload['watch_trial'] = metadata['watch_trial']
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)
    return payload


def backup_snapshot(path):
    """Independent downloadable, checksummed backup; restores through the same importer."""
    path = Path(path)
    content = gzip.compress(path.read_bytes(), mtime=0)
    if len(content) > 5 * 1024 * 1024:
        raise ValueError('Backup exceeds 5 MiB budget; review storage before continuing')
    backup = path.with_name('archive-backup.json.gz')
    backup.write_bytes(content)
    backup.with_suffix('.gz.sha256').write_text(hashlib.sha256(content).hexdigest() + '  ' + backup.name + '\n', encoding='ascii')


def sync_public_archive():
    """At most one read every five minutes; visitors never call NewsData or AI."""
    global _next_check
    # Explicit local/test databases remain isolated unless the URL is also explicit.
    if os.environ.get('NEWS_ARCHIVE_DB') and not os.environ.get('NEWS_ARCHIVE_SNAPSHOT_URL'):
        return dict(_status)
    with _lock:
        if time.monotonic() < _next_check:
            return dict(_status)
        _next_check = time.monotonic() + 300
        try:
            # Use one shared URL per five-minute window so GitHub's CDN cannot
            # add another stale cache interval on top of this process's cache.
            response = requests.get(os.environ.get('NEWS_ARCHIVE_SNAPSHOT_URL', SNAPSHOT_URL),
                                    params={'snapshot_window': int(time.time() // 300)}, timeout=5)
            response.raise_for_status()
            payload = response.json()
            count = restore_snapshot(payload)
            _status.update(updated_at=payload.get('updated_at'), count=count, unavailable=False)
        except (requests.RequestException, ValueError, OSError, sqlite3.Error) as error:
            # Retain the last good database; never replace it with an empty failed response.
            _status['unavailable'] = True
            print('[archive sync unavailable]', type(error).__name__)
        return dict(_status)
