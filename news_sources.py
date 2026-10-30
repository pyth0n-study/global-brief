"""Fetch providers into the article shape used by Global Brief. No AI calls here."""
import requests


class NewsSourceError(RuntimeError):
    pass


def fetch_articles(provider, newsapi_key=None, newsdata_key=None):
    if provider == 'newsapi':
        if not newsapi_key:
            raise NewsSourceError('NEWS_API_KEY is required')
        response = requests.get(
            'https://newsapi.org/v2/everything',
            params={
                'domains': 'nhk.or.jp,asahi.com,mainichi.jp,yomiuri.co.jp,nikkei.com,jiji.com,47news.jp,sankei.com,tokyo-np.co.jp',
                'excludeDomains': 'prtimes.jp,atpress.ne.jp,dreamnews.jp,newscast.co.jp,prlog.jp',
                'pageSize': 20, 'sortBy': 'publishedAt', 'apiKey': newsapi_key,
            }, timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if data.get('status') != 'ok' or not isinstance(data.get('articles'), list):
            raise NewsSourceError('NewsAPI returned an unsuccessful response')
        return data['articles'][:20]
    if provider != 'newsdata':
        raise NewsSourceError('NEWS_PROVIDER must be newsapi or newsdata')
    if not newsdata_key:
        raise NewsSourceError('NEWSDATA_API_KEY is required')

    articles, seen, pages = [], set(), set()
    params = {'language': 'ja', 'category': 'world'}
    # Free responses contain up to 10 articles. Bound requests to two pages.
    for _ in range(2):
        response = requests.get(
            'https://newsdata.io/api/1/latest', params=params.copy(),
            headers={'X-ACCESS-KEY': newsdata_key}, timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if data.get('status') != 'success' or not isinstance(data.get('results'), list):
            raise NewsSourceError('NewsData.io returned an unsuccessful response')
        for item in data['results']:
            url = item.get('link') or ''
            if not url.startswith(('https://', 'http://')) or url in seen:
                continue
            seen.add(url)
            articles.append({
                'title': item.get('title') or '',
                'description': item.get('description') or '',
                'url': url,
                'source': {'name': item.get('source_name') or item.get('source_id') or '不明'},
                'publishedAt': item.get('pubDate'),
                # Provider URL only; no image download or fabricated replacement.
                'urlToImage': item.get('image_url') or None,
            })
        page = data.get('nextPage')
        if len(articles) >= 20 or not page or page in pages or not data['results']:
            break
        pages.add(page)
        params['page'] = page
    return articles[:20]
