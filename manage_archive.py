"""Explicit operator commands; visitors cannot trigger fetching or exporting."""
import argparse
import json
from contextlib import closing
from pathlib import Path
from news_archive import archive_articles, seed_archive, connect


def main():
    parser = argparse.ArgumentParser(description='Manage the source news archive')
    parser.add_argument('action', choices=['fetch', 'export', 'import'])
    parser.add_argument('--file', default='data/archive_export.json')
    args = parser.parse_args()
    seed_archive()
    if args.action == 'fetch':
        import os
        from dotenv import load_dotenv
        from news_sources import fetch_articles
        load_dotenv()
        articles = fetch_articles('newsdata', newsdata_key=os.environ.get('NEWSDATA_API_KEY'))
        print('Archived articles:', archive_articles(articles))
    elif args.action == 'export':
        with closing(connect()) as db:
            rows = [dict(row) for row in db.execute('SELECT * FROM archive_articles ORDER BY first_seen,url')]
        Path(args.file).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Exported articles:', len(rows))
    else:
        rows = json.loads(Path(args.file).read_text(encoding='utf-8'))
        for row in rows:
            archive_articles([row], captured_at=row.get('first_seen'))
        print('Imported articles:', len(rows))


if __name__ == '__main__':
    main()
