"""Reviewed facts and original-source excerpts. Never infer household impacts."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse


def load_connections():
    return json.loads((Path(__file__).parent / 'japan_connection_library.json').read_text(encoding='utf-8'))


def japan_connection(article):
    title = article.get('title') or ''
    description = article.get('description') or article.get('source_description') or ''
    url = article.get('url') or ''
    sources, facts, evidence, ids = [], [], [], []
    for entry in load_connections():
        if any(c in title for c in entry['countries']) and any(t in title for t in entry['topics']):
            facts.append(entry['fact'])
            sources.append(entry['source'])
            ids.append(entry['id'])
    # Quote complete original sentences only, retaining denials/uncertainty.
    terms = ('日本政府', '日本企業', '在日米軍', '嘉手納', '沖縄', 'KDDI', '小泉進次郎防衛相', '小泉防衛相')
    parsed = urlparse(url)
    if parsed.scheme == 'https' and parsed.hostname:
        for sentence in re.split(r'(?<=。)', description):
            sentence = sentence.strip()
            if sentence.endswith('。') and any(term in sentence for term in terms):
                evidence.append(sentence)
                if len(evidence) == 2:
                    break
        if evidence:
            sources.append(dict(label='元記事：引用箇所を確認', url=url))
    matched = bool(facts or evidence)
    return dict(
        relation='\n'.join(facts) if facts else ('' if evidence else '日本との具体的な接点は、現在の確認済みデータでは特定できていません。'),
        evidence=evidence, life='', matched=matched, matched_ids=ids,
        limit='上記は既存の関係・記事の記述です。この記事による生活費やサービスへの影響は確認していません。' if matched else '関係がないという意味ではありません。根拠のない生活への影響は表示しません。',
        sources=sources, reviewed_at='2026-10-29')


def attach_japan_connections(articles):
    return [dict(article, japan_connection=japan_connection(article), thinking_points=thinking_points(article)) for article in articles]


def thinking_points(article):
    """Reading questions, not claims about what occurred or predictions."""
    title = article.get('title') or ''
    if any(word in title for word in ('選挙', '開票', '再選')):
        return ['誰が、何を決める選挙？', '結果は確定している？ それとも予測？', '候補者の主張と、実行された政策は分けて読める？']
    if any(word in title for word in ('AI', '雇用')):
        return ['これは将来の予測？ すでに確認された変化？', '誰の見解で、どんな根拠がある？', '影響を受ける仕事や条件は具体的に示されている？']
    if any(word in title for word in ('攻撃', '殺害', '紛争', '軍')):
        return ['計画・主張と、実際に起きたことを区別できる？', '誰が発表し、別の情報源でも確認されている？', '現地の人への影響は、どこまで分かっている？']
    if any(word in title for word in ('治安', '禁止', '処分', '批判')):
        return ['その対応は、誰をどこまで対象にしている？', '出来事・当事者の説明・評価を分けて読める？', '理由や経緯は、元記事で確認できる？']
    return ['何が確認され、何がまだ分かっていない？', '誰の発表で、どんな根拠がある？', 'この後、何が分かれば理解が深まる？']
