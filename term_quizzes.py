"""Reviewed general-knowledge questions; headlines select terms, not answers."""
import re
import unicodedata
from headline_quizzes import clean_headline

TERMS = [
    dict(term='OPEC', pattern=r'(?<![A-Za-z])OPEC(?![A-Za-z])', question='OPECが協調する政策は？',
         options=['航空輸送', '石油', '宇宙開発'], answer=1,
         explanation='OPEC（石油輸出国機構）は、加盟国の石油政策の調整を目的とする組織です。OPECプラスは非加盟の産油国も含む協力の枠組みです。',
         source='OPEC：組織の目的', url='https://opec.org/assets/assetdb/children-book-english-1.pdf'),
    dict(term='WTO', pattern=r'(?<![A-Za-z])WTO(?![A-Za-z])|世界貿易機関', question='WTOが扱う主なルールは？',
         options=['国際貿易', '国際競技', '航空管制'], answer=0,
         explanation='WTO（世界貿易機関）は、国と国の貿易ルールを扱う国際機関です。',
         source='WTO：組織の役割', url='https://www.wto.org/english/theWTO_e/whatis_e/inbrief_e/inbr00_e.htm'),
    dict(term='国連', pattern=r'国連|国際連合', question='国連が設立された年は？',
         options=['1919年', '1989年', '1945年'], answer=2,
         explanation='国際連合は1945年に設立されました。国際平和と安全の維持などに取り組みます。',
         source='国連：About Us', url='https://www.un.org/en/about-us'),
]

# Definitions are reviewed against the linked official sources. These questions
# describe the term, never infer an event outcome or a single host country.
ABBREVIATIONS = [
    ('APEC', 'アジア太平洋経済協力', 'APECが経済協力を進める地域は？',
     ['ヨーロッパ', 'アジア太平洋', '中南米'], 1,
     'APEC（アジア太平洋経済協力）は、アジア太平洋地域の貿易・投資や経済協力について話し合う枠組みです。',
     '外務省：APEC', 'https://www.mofa.go.jp/files/100169232.pdf'),
    ('G7', '主要7か国', 'G7はどのような場？',
     ['主要国が国際課題を話し合う場', '世界の裁判を行う機関', '航空会社の業界団体'], 0,
     'G7は主要7か国が経済・外交などの国際課題を話し合う非公式な枠組みです。常設の事務局を持つ国際機関とは異なります。',
     'ドイツ外務省：G7', 'https://www.auswaertiges-amt.de/en/aussenpolitik/internationale-organisationen/g7-g20'),
    ('G20', '', 'G20で主に協議される分野は？',
     ['国際スポーツの競技規則', '映画の著作権', '世界経済・金融などの国際課題'], 2,
     'G20は主要な経済を担う国・地域などが、世界経済や金融などの国際課題について協議する枠組みです。',
     '欧州委員会：国際的な協議の枠組み', 'https://finance.ec.europa.eu/eu-and-world/international-fora_en'),
    ('ASEAN', '東南アジア諸国連合', 'ASEANが主に協力を進める地域は？',
     ['東南アジア', '北ヨーロッパ', '南アメリカ'], 0,
     'ASEAN（東南アジア諸国連合）は、東南アジアの国々が地域の平和・安定や経済成長などに向けて協力する枠組みです。',
     'ASEAN：組織紹介', 'https://asean.org/about-asean'),
    ('IMF', '国際通貨基金', 'IMFが担う主な役割は？',
     ['国際郵便の配送', '国際通貨・金融の安定を支える', '世界遺産の登録'], 1,
     'IMF（国際通貨基金）は、国際通貨協力や金融の安定に取り組み、加盟国への政策助言や融資などを行います。',
     'IMF：組織の役割', 'https://www.imf.org/en/About/Factsheets/IMF-at-a-Glance'),
    ('NATO', '北大西洋条約機構', 'NATOの中心的な目的は？',
     ['共通通貨の発行', '世界の貿易ルール作り', '加盟国の安全を守る'], 2,
     'NATO（北大西洋条約機構）は、北米と欧州の国々による政治・軍事同盟です。加盟国の集団防衛を中心に据えています。',
     'NATO：組織紹介', 'https://www.nato.int/en/what-is-nato'),
    ('WHO', '世界保健機関', 'WHOが主に取り組む分野は？',
     ['保健・医療', '国際航空', '金融市場'], 0,
     'WHO（世界保健機関）は、健康の増進や感染症などの保健上の緊急事態への対応を担う国連の専門機関です。',
     'WHO：組織紹介', 'https://www.who.int/about-us'),
    ('EU', '欧州連合', 'EUが統合・協力を進める主な地域は？',
     ['南アメリカ', 'ヨーロッパ', '東南アジア'], 1,
     'EU（欧州連合）は、ヨーロッパの国々が政治・経済などの分野で統合・協力を進める枠組みです。',
     'EU：目的と価値', 'https://european-union.europa.eu/principles-countries-history/principles-and-values/aims-and-values_en'),
]
for term, alias, question, options, answer, explanation, source, url in ABBREVIATIONS:
    pattern = r'(?<![A-Za-z0-9])' + re.escape(term) + r'(?![A-Za-z0-9])'
    if alias: pattern += '|' + re.escape(alias)
    TERMS.append(dict(term=term, pattern=pattern, question=question, options=options,
                      answer=answer, explanation=explanation, source=source, url=url))


def term_quiz_for_article(article):
    # Do not use descriptions: a passing mention need not be the article's topic.
    title = unicodedata.normalize('NFKC', clean_headline(article.get('title', '')))
    for q in TERMS:
        if not re.search(q['pattern'], title): continue
        if q['term'] in ('G7', 'G20') and not re.search(r'会合|首脳|外相|財務|外交|経済|サミット|大臣|閣僚|議長|国際|主要7か国', title): continue
        return dict(q)
    return None
