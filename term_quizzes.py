"""Reviewed general-knowledge questions; headlines select terms, not answers."""
import re

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


def term_quiz_for_article(article):
    # Do not use descriptions: a passing mention need not be the article's topic.
    title = re.sub(r'[（(][^（）()]{1,40}[）)]$', '', article.get('title', '')).strip()
    return next((dict(q) for q in TERMS if re.search(q['pattern'], title)), None)
