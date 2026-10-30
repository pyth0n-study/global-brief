"""Latest archived articles for the public feed, with an offline submission fallback."""
import json
from pathlib import Path
from archive_store import sync_public_archive
from news_archive import seed_archive, read_archive


def load_home_feed():
    fallback = json.loads((Path(__file__).parent / 'data/submission_news.json').read_text(encoding='utf-8'))
    seed_archive()
    status = sync_public_archive()
    rows = read_archive()
    seed = {a['url']: a for a in fallback['articles']}
    # Keep the complete, reviewable demo when no new ingestion has ever succeeded.
    if not any(a.get('published_at') or a['url'] not in seed for a in rows):
        return dict(fallback, live_archive=False)
    articles = []
    for row in rows[:20]:
        item = dict(row)
        item['image'] = item.get('image') or seed.get(item['url'], {}).get('image') or ''
        articles.append(item)
    return dict(articles=articles, captured_at=(status.get('updated_at') or articles[0]['first_seen'])[:10],
                live_archive=True, archive_status=status)
