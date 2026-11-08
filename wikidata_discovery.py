"""Conservative discovery: full person names with role context, formal organizations."""
from datetime import datetime, timedelta
import re
import unicodedata
import requests
from headline_quizzes import clean_headline, mentions

PERSON = r'[ァ-ヶー]{2,}(?:・[ァ-ヶー]{2,}){1,4}'
ORG = r'(?:国際|世界|欧州|アジア|アフリカ|米国|米連邦|国連)[一-龯ァ-ヶー]{2,22}(?:機関|機構|基金|銀行|委員会|理事会|連合)'
ORG_TYPES = {'Q43229', 'Q484652', 'Q327333', 'Q163740', 'Q4830453', 'Q3918', 'Q7278', 'Q79913'}
ROLES = [('国連事務総長', '国際連合の事務総長'), ('政治家',), ('外交官',), ('実業家', '最高経営責任者', 'CEO'),
         ('俳優', '女優'), ('歌手',), ('漫画家',), ('アニメーター',),
         ('記者', 'ジャーナリスト'), ('研究者',), ('科学者',), ('作家',)]
MAX_SEARCHES = 6


def context_role(article, description, term):
    context = clean_headline(article.get('title', '')) + ' ' + (article.get('description') or '')
    for forms in ROLES:
        if not any(f in description for f in forms): continue
        for form in forms:
            before = re.escape(form) + r'(?:の|である|、|・|\s){0,4}' + re.escape(term)
            after = re.escape(term) + r'(?:氏|さん)?(?:は|が|の|、|・|\s){0,3}' + re.escape(form)
            if re.search(before, context) or re.search(after, context): return forms[0]
    return None


def normalized(value):
    return unicodedata.normalize('NFKC', value or '')


def acronym_present(term, article):
    return bool(isinstance(term, str) and re.fullmatch(r'[A-Z][A-Z0-9]{1,9}', term) and mentions(term, normalized(clean_headline(article.get('title', '')))))


def paired_name(term, formal, article):
    if not isinstance(term, str) or not isinstance(formal, str) or not 4 <= len(formal) <= 80 or not re.search(r'[一-龯]', formal): return False
    context = normalized(clean_headline(article.get('title', '')) + ' ' + (article.get('description') or ''))
    formal = normalized(formal)
    before = r'(?<![一-龯ァ-ヶー])' + re.escape(formal) + r'\s*\(\s*' + re.escape(term) + r'\s*\)'
    after = r'(?<![A-Za-z0-9])' + re.escape(term) + r'\s*\(\s*' + re.escape(formal) + r'\s*\)'
    return bool(re.search(before, context) or re.search(after, context))


def expanded_name(term, article):
    context = normalized(clean_headline(article.get('title', '')) + ' ' + (article.get('description') or ''))
    names = re.findall(r'[一-龯ァ-ヶー]{4,80}', context)
    return next((n for n in names if paired_name(term, n, article)), None)


def candidates(article):
    title = clean_headline(article.get('title', ''))
    if re.search(r'ドラマ|映画|小説|ゲーム|架空|同名|ものまね|なりすまし', title): return []
    people = [(m.group(1), 'person') for m in re.finditer(
        '(' + PERSON + r')(?:氏|さん|大統領|首相|国連事務総長|事務総長|議長|委員長|代表|知事)', title)]
    orgs = [(m.group(), 'organization') for m in re.finditer(ORG, title)]
    title = normalized(title)
    context = normalized(title + ' ' + (article.get('description') or ''))
    acronyms = [(m.group(), 'acronym') for m in re.finditer(r'(?<![A-Za-z0-9])[A-Z][A-Z0-9]{1,9}(?![A-Za-z0-9])', title)
                if re.search(r'\(\s*' + re.escape(m.group()) + r'\s*\)|' + re.escape(m.group()) + r'\s*\(', context)]
    return list(dict.fromkeys(people + orgs + acronyms))


def valid_identity(note):
    proof = note.get('identity', {})
    if not isinstance(proof, dict): return False
    term, kind = proof.get('term', ''), proof.get('kind')
    if not isinstance(term, str) or not isinstance(proof.get('types'), list) or not all(isinstance(t, str) for t in proof['types']): return False
    if proof.get('method') != 'exact-ja-role-v1' or proof.get('unique') is not True: return False
    if term not in proof.get('matched_names', []): return False
    types = set(proof.get('types', []))
    if kind == 'person':
        return bool(re.fullmatch(PERSON, term) and 'Q5' in types and proof.get('role') in [r[0] for r in ROLES])
    if kind == 'acronym':
        formal = proof.get('formal_name')
        return bool(re.fullmatch(r'[A-Z][A-Z0-9]{1,9}', term) and types
                    and not types & {'Q5', 'Q4167410', 'Q13406463'}
                    and isinstance(formal, str) and 4 <= len(formal) <= 80
                    and re.search(r'[一-龯]', formal) and formal in proof.get('matched_names', []))
    return bool(kind == 'organization' and re.fullmatch(ORG, term) and types & ORG_TYPES and 'Q5' not in types)


def dynamic_matches(article, entries):
    allowed = dict(candidates(article))
    for qid, note in entries.items():
        if not isinstance(note, dict) or not valid_identity(note): continue
        proof = note['identity']
        if allowed.get(proof['term']) != proof['kind']: continue
        if proof['kind'] == 'acronym' and not paired_name(proof['term'], proof['formal_name'], article): continue
        if proof['kind'] == 'person' and context_role(article, note.get('description', ''), proof['term']) != proof['role']: continue
        yield proof['term'], qid


def discover(payload, session, now, interactive=False):
    from wikidata_notes import API, USER_AGENT, ENTITIES, identified_terms, valid_note
    cache = payload['wikidata']
    deferred = cache.get('deferred_until')
    if deferred:
        try:
            if now < datetime.fromisoformat(deferred): return 0
        except (TypeError, ValueError): pass
    entries, lookups = cache['entries'], cache.setdefault('lookups', {})
    articles = sorted(payload.get('articles', []), key=lambda a: a.get('published_at') or a.get('first_seen', ''), reverse=True)[:20]
    pending = {}
    for article in articles:
        known = {word for _, words in ENTITIES.values() for word in words}
        for term, kind in candidates(article):
            if term in known: continue
            checked = lookups.get(term, {}).get('checked_at')
            if checked:
                try:
                    if now - datetime.fromisoformat(checked) < timedelta(days=1): continue
                except (ValueError, TypeError): pass
            if any(t == term and valid_note(q, entries[q], now) for t, q in dynamic_matches(article, entries)): continue
            pending.setdefault(term, (kind, article))
    client = session or requests
    common = {} if interactive else {'maxlag': 5}
    selected = {}
    try:
        for term, (kind, article) in list(pending.items())[:MAX_SEARCHES]:
            search_term = expanded_name(term, article) if kind == 'acronym' else term
            if not search_term: continue
            lookups[term] = {'checked_at': now.isoformat(), 'status': 'unresolved'}
            response = client.get(API, params=dict(action='wbsearchentities', search=search_term,
                language='ja', uselang='ja', format='json', limit=10, **common),
                headers={'User-Agent': USER_AGENT}, timeout=15)
            response.raise_for_status()
            body = response.json()
            if body.get('error'): raise ValueError('Deferred')
            hits = body.get('search', [])
            # A full result page may hide another exact match; never accept it.
            exact = [h for h in hits if h.get('match', {}).get('text') == search_term]
            if len(hits) >= 10 or 'search-continue' in body or len(exact) != 1: continue
            qid = exact[0].get('id', '')
            if re.fullmatch(r'Q[1-9][0-9]*', qid) and qid not in ENTITIES:
                selected[term] = (qid, kind, article)
        if not selected: return 0
        response = client.get(API, params=dict(action='wbgetentities', ids='|'.join(sorted({v[0] for v in selected.values()})),
            props='labels|aliases|descriptions|claims|info', languages='ja|en', format='json', **common),
            headers={'User-Agent': USER_AGENT}, timeout=15)
        response.raise_for_status()
        body = response.json()
        if body.get('error'): raise ValueError('Deferred')
        count = 0
        for term, (qid, kind, article) in selected.items():
            entity = body.get('entities', {}).get(qid, {})
            if entity.get('id') != qid or 'missing' in entity or 'redirects' in entity: continue
            label = entity.get('labels', {}).get('ja', {}).get('value', '')
            names = [label] + [a.get('value') for a in entity.get('aliases', {}).get('ja', [])]
            if term not in names: continue
            types = [c.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')
                     for c in entity.get('claims', {}).get('P31', []) if c.get('rank') != 'deprecated']
            text = entity.get('descriptions', {}).get('ja', {}).get('value', '')
            formal = next((normalized(n) for n in names if isinstance(n, str) and paired_name(term, n, article)), None) if kind == 'acronym' else None
            if kind == 'acronym' and not formal: continue
            proof = dict(method='exact-ja-role-v1', unique=True, term=term, kind=kind,
                         matched_names=[term] + ([formal] if formal else []), formal_name=formal, types=[t for t in types if isinstance(t, str)],
                         role=context_role(article, text, term) if kind == 'person' else None)
            note = dict(qid=qid, label=label, english_label=entity.get('labels', {}).get('en', {}).get('value', ''),
                        description=text, revision=entity.get('lastrevid'), fetched_at=now.isoformat(), identity=proof)
            accepted = valid_note(qid, note, now)
            if accepted:
                entries[qid] = accepted
                lookups[term]['status'] = 'matched'
                count += 1
        return count
    except (requests.RequestException, ValueError, TypeError, AttributeError, KeyError):
        cache['deferred_until'] = (now + timedelta(hours=1)).isoformat()
        print('Wikidata discovery deferred; unresolved introductions hidden')
        return 0
    finally:
        cache['lookups'] = dict(sorted(lookups.items(), key=lambda p: p[1].get('checked_at', ''), reverse=True)[:256])
