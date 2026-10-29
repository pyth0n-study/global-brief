"""Reviewed background library; conservative country AND topic matching."""
import json
from pathlib import Path


def load_timelines():
    return json.loads((Path(__file__).parent / 'timeline_library.json').read_text(encoding='utf-8'))


def timeline_for_article(article):
    # Use the headline for subject matching: incidental description mentions
    # should not attach an unrelated country's history.
    title = article.get('title') or ''
    if 'ブラジル' in title and any(w in title for w in ('大統領選', '選挙制度', '民主化')):
        return 'brazil_elections'
    if '中国' in title and any(w in title for w in ('貿易', 'WTO', '関税', '輸出規制')):
        return 'china_trade'
    if ('日中' in title or ('日本' in title and '中国' in title)) and any(w in title for w in ('国交', '外交', '共同声明', '平和友好', '首脳会談')):
        return 'japan_china_diplomacy'
    return None


def attach_timelines(articles):
    """Re-evaluate on display so old caches also follow the current library."""
    library = load_timelines()
    result = []
    for article in articles:
        key = timeline_for_article(article)
        result.append(dict(article, timeline_id=key, timeline=library.get(key)))
    return result
