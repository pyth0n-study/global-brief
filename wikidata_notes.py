"""Cached Wikidata descriptions for explicitly identified entities. No AI calls."""
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re

import requests
from headline_quizzes import clean_headline, mentions

API = 'https://www.wikidata.org/w/api.php'
USER_AGENT = 'GlobalBrief/1.0 (https://global-brief-00i2.onrender.com/about)'
MAX_AGE = timedelta(days=7)
# Verified identity bindings, not the first search hit. Short ambiguous names
# and unsupported people are intentionally omitted from this initial trial.
ENTITIES = {
    'Q8333': ('Federal Bureau of Investigation', ('FBI', '米連邦捜査局', '連邦捜査局')),
    'Q3304418': ('Meghan, Duchess of Sussex', ('メーガン妃', 'メーガン・マークル', 'サセックス公爵夫人メーガン')),
    'Q8901': ('European Central Bank', ('ECB', '欧州中央銀行')),
    'Q23548': ('National Aeronautics and Space Administration', ('NASA', '米航空宇宙局')),
    'Q37230': ('Central Intelligence Agency', ('CIA', '米中央情報局')),
    'Q7804': ('International Monetary Fund', ('IMF', '国際通貨基金')),
    'Q7817': ('World Health Organization', ('WHO', '世界保健機関')),
    'Q7184': ('NATO', ('NATO', '北大西洋条約機構')),
}


def identified_terms(title):
    title = clean_headline(title)
    # Fictional works / impersonations can share an otherwise exact name.
    if re.search(r'ドラマ|映画|小説|ゲーム|架空|同名|ものまね|なりすまし', title): return []
    found = []
    for qid, (_, words) in ENTITIES.items():
        matches = [(m.start(), w) for w in words for m in mentions(w, title)]
        if matches:
            position, word = min(matches, key=lambda x: (x[0], -len(x[1])))
            found.append((position, word, qid))
    return sorted(found)


def valid_note(qid, note, now=None):
    if qid not in ENTITIES or not isinstance(note, dict): return None
    now = now or datetime.now(timezone.utc)
    try:
        stamp = datetime.fromisoformat(note['fetched_at'])
        if not stamp.tzinfo or not timedelta(0) <= now - stamp <= MAX_AGE: return None
    except (KeyError, TypeError, ValueError): return None
    text, label, revision = note.get('description'), note.get('label'), note.get('revision')
    if note.get('qid') != qid or note.get('english_label') != ENTITIES[qid][0]: return None
    if not isinstance(text, str) or not 4 <= len(text) <= 180 or not re.search(r'[ぁ-んァ-ヶ一-龯]', text): return None
    if not isinstance(label, str) or not 1 <= len(label) <= 80: return None
    if re.search(r'[<>\n\r]|曖昧さ回避|ウィキメディア|disambiguation', text, re.I): return None
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1: return None
    return dict(qid=qid, label=label, description=text, fetched_at=note['fetched_at'],
                english_label=note['english_label'], revision=revision,
                fetched_day=stamp.astimezone(timezone(timedelta(hours=9))).date().isoformat(),
                source='Wikidata', url=f'https://www.wikidata.org/w/index.php?title={qid}&oldid={revision}')


def cached_notes():
    from archive_store import _status
    if isinstance(_status.get('wikidata'), dict): return _status['wikidata']
    try:
        return json.loads((Path(__file__).parent / 'data/wikidata_notes.json').read_text(encoding='utf-8'))
    except (OSError, ValueError): return {}


def notes_for_article(article, cache=None, now=None):
    cache = cache if cache is not None else cached_notes()
    entries = cache.get('entries', {}) if isinstance(cache, dict) else {}
    if not isinstance(entries, dict): return []
    result = []
    for _, term, qid in identified_terms(article.get('title', '')):
        note = valid_note(qid, entries.get(qid), now)
        if note: result.append(dict(note, term=term))
    return result[:2]


def refresh(payload, session=None, now=None, interactive=False):
    """One bounded batch request during ingestion; never on page views."""
    now = now or datetime.now(timezone.utc)
    if 'wikidata' not in payload:
        try:
            payload['wikidata'] = json.loads((Path(__file__).parent / 'data/wikidata_notes.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            payload['wikidata'] = {'version': 1, 'entries': {}}
    cache = payload['wikidata']
    entries = cache.setdefault('entries', {})
    articles = sorted(payload.get('articles', []), key=lambda a: a.get('published_at') or a.get('first_seen', ''), reverse=True)[:20]
    ids = sorted({qid for a in articles for _, _, qid in identified_terms(a.get('title', ''))
                  if not valid_note(qid, entries.get(qid), now)})
    if not ids: return 0
    # Drop stale entries even if the refresh fails; no old cached biography fallback.
    for qid in ids: entries.pop(qid, None)
    try:
        response = (session or requests).get(API, params={
            'action': 'wbgetentities', 'ids': '|'.join(ids), 'props': 'labels|descriptions|info',
            'languages': 'ja|en', 'format': 'json', **({} if interactive else {'maxlag': 5})},
            headers={'User-Agent': USER_AGENT}, timeout=15)
        response.raise_for_status()
        body = response.json()
        if body.get('error'):
            print('Wikidata deferred; descriptions hidden until a later scheduled refresh')
            return 0
        entities = body.get('entities', {})
        count = 0
        for qid in ids:
            entity = entities.get(qid, {})
            if entity.get('id') != qid or 'missing' in entity or 'redirects' in entity: continue
            note = dict(qid=qid, label=entity.get('labels', {}).get('ja', {}).get('value'),
                        english_label=entity.get('labels', {}).get('en', {}).get('value'),
                        description=entity.get('descriptions', {}).get('ja', {}).get('value'),
                        revision=entity.get('lastrevid'), fetched_at=now.isoformat())
            accepted = valid_note(qid, note, now)
            if accepted:
                entries[qid] = accepted
                count += 1
        return count
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        print('Wikidata unavailable; unresolved introductions hidden')
        return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True)
    args = parser.parse_args()
    path = Path(args.file)
    payload = json.loads(path.read_text(encoding='utf-8'))
    print('Wikidata descriptions fetched:', refresh(payload))
    from watch_points import save
    save(path, payload)
