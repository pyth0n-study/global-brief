"""Conservative year questions from explicitly delimited source chronologies."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import re
from urllib.parse import urlparse

YEAR = re.compile(r'(?<!\d)([12]\d{3})年[：:]')
COMPLETE = re.compile(r'(?:宣言|発表|締結|設立|発足|就任|訪問|来韓|来日|独立|加盟|開幕|開催|初選出|選出|承認|結成|実施|開通)(?:した|する|された|される)?[。．]?$')
NAMED_ROLE = re.compile(r'.{2,}(?:首相|大統領|外相)(?:が|は)')
EXPLICIT_EVENT = re.compile(
    r'(?:.{2,}(?:団|党|組合|協会|機構|委員会)(?:を)?結成'
    r'|.{2,}制度を実施|.{2,}鉄道が開通)'
    r'(?:した|された)?[。．]?$'
)


def history_quiz_for_article(article):
    from headline_quizzes import clean_headline
    title = clean_headline(article.get('title', ''))
    if not re.fullmatch(r'(?:今日|きょう)の歴史[（(]\d{1,2}月\d{1,2}日[）)]', title): return None
    url = article.get('url', '')
    if urlparse(url).scheme not in {'https', 'http'} or not urlparse(url).netloc: return None
    text = article.get('description') or ''
    if len(text) > 5000 or re.search(r'[<>]', text): return None
    markers = list(YEAR.finditer(text))
    if not markers or text[:markers[0].start()].strip(): return None
    counts = Counter(m[1] for m in markers)
    records = []
    current_year = datetime.now(timezone.utc).year
    for i, marker in enumerate(markers):
        year = marker[1]
        end = markers[i+1].start() if i+1 < len(markers) else len(text)
        body = text[marker.end():end].strip()
        if i == len(markers)-1 and not body.endswith(('。', '．')): continue
        if counts[year] != 1 or not 1000 <= int(year) <= current_year: continue
        if not 8 <= len(body) <= 180 or not COMPLETE.search(body): continue
        if re.search(r'[?？…]|\.{3}|疑い|未確認|という説|とされ|予定|見込み|計画|ではない|でない|じゃない|ではなく|否定', body): continue
        # A single bounded entry must contain one event, not several sentences.
        if re.search(r'[。．].', body): continue
        records.append((year, body, text[marker.start():end].strip()))
    if len(records) < 3: return None
    unique = [r for r in records if sum(other[1] == r[1] for other in records) == 1]
    if len(unique) < 3: return None
    # A named actor or a concrete target makes the event identifiable.
    questions = [r for r in unique if NAMED_ROLE.search(r[1]) or EXPLICIT_EVENT.fullmatch(r[1])]
    if not questions: return None
    seed = int(hashlib.sha256((title + text).encode()).hexdigest()[:8], 16)
    year, body, evidence = questions[seed % len(questions)]
    other_years = [r[0] + '年' for r in unique if r[0] != year]
    options = other_years[:2]
    answer = seed % 3
    options.insert(answer, year + '年')
    return dict(kind='history', term='歴史クイズ', question='この出来事があった年は？\n' + body,
                options=options, answer=answer, evidence=evidence,
                explanation='説明文の原文：' + evidence, source='記事の出典を確認', url=url)
