"""Questions from an automatically resolved acronym and article-attested full name."""
import hashlib
import re
from wikidata_discovery import ORG_TYPES, paired_name, acronym_present


def acronym_quiz_for_article(article, notes):
    for note in notes:
        proof = note.get('identity', {})
        term, formal = proof.get('term'), proof.get('formal_name')
        if proof.get('kind') != 'acronym' or not acronym_present(term, article): continue
        if not paired_name(term, formal, article): continue
        pool = (['国際連合', '世界保健機関', '世界貿易機関', '国際通貨基金']
                if set(proof.get('types', [])) & ORG_TYPES or re.search(r'機関|機構|連合|銀行|基金|委員会', formal)
                else ['国内総生産', '消費者物価指数', '関税', '失業率'])
        context = (article.get('title') or '') + ' ' + (article.get('description') or '')
        wrong = [word for word in pool if word != formal and word not in context
                 and word not in formal and formal not in word]
        if len(wrong) < 2: continue
        options = wrong[:2]
        answer = int(hashlib.sha256((term + article['title']).encode()).hexdigest()[:8], 16) % 3
        options.insert(answer, formal)
        return dict(kind='acronym', term=term, question=f'{term}が指すのは？', options=options,
                    answer=answer, explanation=note['description'],
                    source='Wikidata：' + note['label'] + '（取得日 ' + note['fetched_day'] + '）',
                    url=note['url'])
    return None
