"""Latest archived articles for the public feed, with an offline submission fallback."""
import json
import hashlib
import re
from contextlib import closing
from pathlib import Path
from archive_store import sync_public_archive
from news_archive import seed_archive, read_archive, connect


def load_home_feed(article_id=''):
    fallback = json.loads((Path(__file__).parent / 'data/submission_news.json').read_text(encoding='utf-8'))
    seed_archive()
    status = sync_public_archive()
    rows = read_archive()
    if article_id:
        if not re.fullmatch(r'[a-f0-9]{32}', article_id):
            return dict(fallback, requested_not_found=True)
        with closing(connect()) as db:
            target = next((dict(row) for row in db.execute('SELECT * FROM archive_articles')
                           if hashlib.md5(row['url'].encode()).hexdigest() == article_id), None)
        if target:
            rows = [target] + [row for row in rows if row['url'] != target['url']]
        else:
            target = next((a for a in fallback['articles'] if hashlib.md5(a['url'].encode()).hexdigest() == article_id), None)
            if not target:
                return dict(fallback, requested_not_found=True)
            return dict(fallback, articles=[target] + [a for a in fallback['articles'] if a['url'] != target['url']], live_archive=False)
    seed = {a['url']: a for a in fallback['articles']}
    # Keep the complete, reviewable demo when no new ingestion has ever succeeded.
    if not article_id and not any(a.get('published_at') or a['url'] not in seed for a in rows):
        return dict(fallback, live_archive=False)
    articles = []
    for row in rows[:20]:
        item = dict(row)
        item['image'] = item.get('image') or seed.get(item['url'], {}).get('image') or ''
        articles.append(item)
    return dict(articles=articles, captured_at=(status.get('updated_at') or articles[0]['first_seen'])[:10],
                live_archive=True, archive_status=status)
