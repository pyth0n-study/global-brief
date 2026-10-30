"""Reviewed reference material stays separate from the news archive."""
from timeline_library import load_timelines
import json
from pathlib import Path

GUIDES = [
    ('brazil_elections', ['brazil'], 'elections', 'ブラジルの選挙と民主化', '軍政から民政への移行と、直接選挙が戻るまでの節目を知る。'),
    ('china_trade', ['china'], 'trade', '中国と世界の貿易ルール', '中国のWTO加盟を、国際貿易制度の歩みの中で読む。'),
    ('japan_china_diplomacy', ['japan', 'china'], 'diplomacy', '日中関係の基本文書', '国交正常化から平和友好条約、共同宣言へ。関係の基礎となる文書を知る。'),
]

OVERVIEWS = {
    'brazil_elections': 'ブラジルの大統領選を読む前に、国民が大統領を直接選ぶ制度にも移行の歴史があることを押さえます。軍政が終わった1985年には、まだ国民による直接選挙ではありませんでした。1988年の新憲法を経て、1989年に直接選挙が復活しました。以下の資料で、この制度の歩みを確認できます。',
    'china_trade': '中国の貿易を読む入口のひとつは、国際的なルールを扱うWTOとの関係です。WTOは1995年に発足し、中国は2001年に加盟しました。その前にはGATTが国際貿易のルールを支えていました。ここでは制度の歩みを紹介し、個別の関税や輸出規制の原因までは断定しません。',
    'japan_china_diplomacy': '日中関係を知る入口として、両国の関係を形づくる基本文書を振り返ります。1972年の共同声明によって国交が正常化し、1978年には平和友好条約が発効しました。1998年には友好協力に関する共同宣言が発表されています。こうした文書があることと、個別の問題で対立がないことは別です。',
}


def guides_for(country='', theme=''):
    library = load_timelines()
    guides = [dict(id=key, countries=countries, theme=topic, title=title, intro=intro, overview=OVERVIEWS[key], **library[key])
        for key, countries, topic, title, intro in GUIDES
        if (not country or country in countries) and (not theme or theme == topic)]
    war = json.loads((Path(__file__).parent / 'data/russia_ukraine_background.json').read_text(encoding='utf-8'))
    if (not country or country in war['countries']) and (not theme or theme == war['theme']):
        guides.insert(0, war)
    return guides
