"""Deterministic headline recall, not verification of reported events."""
import hashlib
import re

# Each group has disjoint spellings. Distractors must belong to the same group
# and must not occur anywhere in the headline. No inferred roles or biography.
GROUPS = {
    '組織': ['FBI', 'CIA', 'NASA', 'ECB', 'FRB', 'IMF', 'WHO', 'NATO', 'EU', '国連', 'WTO', 'OPEC'],
    '人物': ['メーガン妃', 'ヘンリー王子', 'トランプ氏', 'トランプ大統領', 'バイデン氏', 'プーチン大統領', 'ゼレンスキー大統領', '習近平氏', '小池都知事'],
    '地域': ['欧州', '中東', '北米', '南米', '東南アジア', '香港', 'マカオ', '台北', 'ロンドン', 'パリ', 'モスクワ', 'ガラパゴス諸島'],
    '経済指標': ['NYダウ', '日経平均', '失業率', '就業者数', '雇用統計', '消費者物価指数', 'GDP'],
    '話題': ['気温', '原料高', '値上げ', '利上げ', '貿易', '関税', '選挙', '放送局', '旅客機', '路線バス'],
}


def clean_headline(title):
    # Strip only trailing publisher parentheses, including nested (ANN).
    title = (title or '').strip()
    while title.endswith((')', '）')):
        depth = 0
        start = None
        for i in range(len(title) - 1, -1, -1):
            if title[i] in ')）': depth += 1
            elif title[i] in '(（':
                depth -= 1
                if depth == 0:
                    start = i
                    break
        if start is None: break
        suffix = title[start:]
        if not any(s in suffix for s in ('通信', 'ニュース', '新聞', 'ANN', '日本版', '日本語版')): break
        title = title[:start].rstrip()
    return title


def mentions(word, title):
    if word.isascii():
        return list(re.finditer(r'(?<![A-Za-z0-9])' + re.escape(word) + r'(?![A-Za-z0-9])', title))
    return list(re.finditer(re.escape(word), title))


def headline_quiz_for_article(article):
    title = clean_headline(article.get('title'))
    if not 12 <= len(title) <= 130 or re.search(r'[……]|\.{3}|[<>\n\r]|[?？]', title): return None
    # Headings, incomplete teasers and all-negative mentions make poor questions.
    if title.startswith(('今日の歴史', 'きょうの歴史')) or re.search(r'ではない|でない|じゃない|ではなく', title): return None
    candidates = []
    for group, words in GROUPS.items():
        for word in words:
            found = mentions(word, title)
            if len(found) != 1: continue
            match = found[0]
            # Do not cut a word embedded in another katakana word, e.g. パリ in パリティ.
            if re.fullmatch(r'[ァ-ヺー]+', word) and (
                (match.start() and re.match(r'[ァ-ヺー]', title[match.start()-1])) or
                (match.end() < len(title) and re.match(r'[ァ-ヺー]', title[match.end()]))): continue
            if len(title) - len(word) < 8: continue
            distractors = [w for w in words if w != word and not mentions(w, title)
                           and w not in word and word not in w]
            if len(distractors) < 2: continue
            candidates.append((list(GROUPS).index(group), match.start(), word, match, distractors, group))
    if not candidates: return None
    _, _, word, match, distractors, group = min(candidates, key=lambda c: (c[0], c[1]))
    seed = int(hashlib.sha256(title.encode()).hexdigest()[:8], 16)
    # Stable answer placement across reloads, rather than always the middle choice.
    wrong = [distractors[seed % len(distractors)], distractors[(seed + 1) % len(distractors)]]
    options = wrong[:]
    answer = seed % 3
    options.insert(answer, word)
    masked = title[:match.start()] + '［　？　］' + title[match.end():]
    return dict(kind='headline', term='見出しクイズ', question=masked,
                options=options, answer=answer, evidence=title, category=group,
                explanation='取得した見出しの原文：' + title,
                source='見出しの出典を確認', url=article.get('url', ''))
