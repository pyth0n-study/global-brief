"""Bounded scheduled ingestion. Failures leave the previously published snapshot intact."""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from archive_store import restore_snapshot, export_snapshot, backup_snapshot
from news_archive import seed_archive, archive_articles
from news_sources import fetch_articles


def run(folder, fetch=False):
    folder = Path(folder)
    path = folder / 'archive.json'
    if path.exists():
        restore_snapshot(json.loads(path.read_text(encoding='utf-8')))
    seed_archive()
    if fetch:
        load_dotenv()
        articles = fetch_articles('newsdata', newsdata_key=os.environ.get('NEWSDATA_API_KEY'))
        if not articles:
            raise ValueError('No articles received; keeping the previous published archive')
        archive_articles(articles)
    payload = export_snapshot(path)
    backup_snapshot(path)
    print('Archive snapshot ready:', payload['count'], 'articles')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', required=True)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    run(args.folder, args.fetch)
