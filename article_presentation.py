"""Conservative presentation rules; no generated facts or external requests."""
import re
from urllib.parse import urlparse

# Regional map coordinates use the bundled Natural Earth projection.
COUNTRIES = [
    ('スペイン', 'ESP', ('スペイン',), ['ポルトガル', 'スペイン', 'フランス'], '460 175 85 65', [(476,213),(488,213),(505,196)]),
    ('アメリカ', 'USA', ('アメリカ', '米国', '米中間選挙', '米軍'), ['メキシコ', 'アメリカ', 'カナダ'], '180 145 160 110', [(250,244),(260,204),(260,165)]),
    ('イスラエル', 'ISR', ('イスラエル',), ['ヨルダン', 'イスラエル', 'レバノン'], '565 215 42 40', [(592,232),(587,230),(590,222)]),
    ('韓国', 'KOR', ('韓国',), ['日本', '韓国', '中国'], '735 190 115 70', [(821,223),(806,223),(764,223)]),
    ('フランス', 'FRA', ('フランス', '仏BNP', '仏極右'), ['スペイン', 'フランス', 'ドイツ'], '465 155 100 95', [(490,211),(505,196),(525,190)]),
    ('ブラジル', 'BRA', ('ブラジル',), ['アルゼンチン', 'ブラジル', 'ペルー'], '300 270 135 155', [(344,382),(375,331),(324,320)]),
    ('モンゴル', 'MNG', ('モンゴル',), ['カザフスタン', 'モンゴル', '中国'], '650 155 165 110', [(723,194),(752,196),(754,222)]),
    ('中国', 'CHN', ('中国',), ['モンゴル', '中国', 'インド'], '660 160 155 130', [(752,196),(754,222),(692,258)]),
    ('日本', 'JPN', ('日本',), ['韓国', '日本', '中国'], '735 185 150 100', [(806,223),(835,220),(764,223)]),
    ('イラン', 'IRN', ('イラン',), ['トルコ', 'イラン', 'イラク'], '560 195 130 90', [(586,219),(632,229),(608,229)]),
    ('ウクライナ', 'UKR', ('ウクライナ',), ['ポーランド', 'ウクライナ', 'ルーマニア'], '525 150 110 85', [(546,185),(579,183),(561,198)]),
    ('ロシア', 'RUS', ('ロシア',), ['カザフスタン', 'ロシア', '中国'], '610 100 270 170', [(723,194),(700,160),(754,222)]),
    ('ドイツ', 'DEU', ('ドイツ',), ['フランス', 'ドイツ', 'ポーランド'], '470 145 110 90', [(505,196),(525,185),(546,185)]),
    ('イギリス', 'GBR', ('イギリス', '英国'), ['アイルランド', 'イギリス', 'フランス'], '445 140 105 95', [(480,182),(495,178),(505,196)]),
    ('北朝鮮', 'PRK', ('北朝鮮',), ['中国', '北朝鮮', '韓国'], '755 185 90 65', [(777,216),(810,211),(809,220)]),
    ('マリ', 'MLI', ('マリ',), ['モーリタニア', 'マリ', 'ニジェール'], '445 225 110 85', [(474,254),(490,261),(522,261)]),
]
# Explicit country names and unambiguous headline abbreviations only.
COUNTRIES += [
    ('インド', 'IND', ('インド', '印首都', '印政府', '印首相'), ['パキスタン', 'インド', 'バングラデシュ'], '630 215 115 100', [(668,248),(692,258),(716,258)]),
    ('エクアドル', 'ECU', ('エクアドル',), ['コロンビア', 'エクアドル', 'ペルー'], '280 260 90 100', [(331,284),(318,300),(324,320)]),
    ('トルコ', 'TUR', ('トルコ',), ['ギリシャ', 'トルコ', 'イラン'], '540 185 115 80', [(564,213),(592,213),(632,229)]),
    ('カナダ', 'CAN', ('カナダ',), ['アメリカ', 'カナダ', 'メキシコ'], '165 90 220 190', [(260,204),(260,165),(250,244)]),
    ('オーストラリア', 'AUS', ('オーストラリア',), ['ニュージーランド', 'オーストラリア', 'インドネシア'], '755 285 230 155', [(950,405),(862,369),(806,312)]),
    ('イタリア', 'ITA', ('イタリア',), ['フランス', 'イタリア', 'ギリシャ'], '480 170 100 80', [(505,196),(535,212),(564,213)]),
    ('フィリピン', 'PHL', ('フィリピン',), ['ベトナム', 'フィリピン', 'インドネシア'], '745 245 110 100', [(777,274),(813,276),(806,312)]),
    ('南アフリカ', 'ZAF', ('南アフリカ', '南ア共和国'), ['ナミビア', '南アフリカ', 'モザンビーク'], '490 335 130 100', [(535,373),(553,398),(580,371)]),
]

# Additional regions use pins checked against the bundled Natural Earth polygons.
COUNTRIES += [
    ('ケニア', 'KEN', ('ケニア',), ['タンザニア', 'ケニア', 'ウガンダ'], '562 278 60 60', [(585.2, 314.1), (592.6, 299.1), (579.0, 296.9)]),
    ('ソマリア', 'SOM', ('ソマリア',), ['エチオピア', 'ソマリア', 'ケニア'], '571 257 63 63', [(598.7, 279.6), (612.6, 288.5), (592.6, 299.1)]),
    ('チリ', 'CHL', ('チリ',), ['アルゼンチン', 'チリ', 'ボリビア'], '306 312 72 117', [(344.7, 382.4), (325.7, 379.4), (344.6, 336.2)]),
    ('パプアニューギニア', 'PNG', ('パプアニューギニア',), ['ソロモン諸島', 'パプアニューギニア', 'バヌアツ'], '835 296 83 60', [(888.8, 317.6), (856.7, 314.8), (908.1, 333.8)]),
    ('インドネシア', 'IDN', ('インドネシア',), ['マレーシア', 'インドネシア', 'フィリピン'], '757 249 60 70', [(779.7, 291.5), (778.6, 299.8), (797.2, 265.1)]),
    ('ベトナム', 'VNM', ('ベトナム',), ['タイ', 'ベトナム', 'カンボジア'], '729 239 60 60', [(748.0, 271.0), (760.3, 262.3), (756.7, 272.1)]),
    ('タイ', 'THA', ('タイ',), ['ミャンマー', 'タイ', 'カンボジア'], '716 228 60 69', [(736.5, 257.4), (748.0, 271.0), (756.7, 272.1)]),
    ('マレーシア', 'MYS', ('マレーシア',), ['タイ', 'マレーシア', 'インドネシア'], '729 245 72 74', [(748.0, 271.0), (779.7, 291.5), (778.6, 299.8)]),
    ('ニュージーランド', 'NZL', ('ニュージーランド',), ['バヌアツ', 'ニュージーランド', 'フィジー'], '893 319 60 98', [(908.1, 333.8), (916.5, 396.8), (935.1, 339.6)]),
]
HEADLINE_ALIASES = {
    'RUS': ('露統計局', '露政府', '露軍', '露大統領'),
    'GBR': ('英首相', '英政府', '英議会'),
    'USA': ('米大統領', '米政府', '米議会', '米首都', '米アトランタ', '米ニューヨーク', '米ロサンゼルス', '米ワシントン'),
    'FRA': ('仏大統領', '仏政府'),
    'DEU': ('独首相', '独政府'),
}



def quiz_for_article(article):
    # Headline only: a dateline in the description need not be the subject country.
    from headline_quizzes import clean_headline
    title = clean_headline(article.get('title', ''))
    def country_mention(word):
        if re.fullmatch(r'[ァ-ヺー]+', word):
            # Avoid incidental substrings: ソマリア / マリーナ / マリオ, etc.
            return re.search(r'(?<![ァ-ヺー])' + re.escape(word) + r'(?![ァ-ヺー])', title)
        return re.search(re.escape(word), title)
    matches = [(match.start(), row) for row in COUNTRIES for word in row[2] + HEADLINE_ALIASES.get(row[1], ())
               if (match := country_mention(word))]
    if not matches:
        return None
    _, row = min(matches, key=lambda match: match[0])
    name, code, _, options, region, pins = row
    return dict(name=name, code=code, options=options, region=region, pins=pins)


def usable_image(url):
    parsed = urlparse(url or '')
    # Visually reviewed: this specific image contains only a repeated headline.
    # Do not classify all OGP images this way; many contain real photographs.
    if parsed.hostname == 'image.news.livedoor.com' and parsed.path.endswith('/ogp_image_32679556_3f268f2d07b5.jpg'):
        return ''
    # Yahoo's default.jpg is its service logo, not a photo of the event.
    if parsed.hostname and parsed.hostname.endswith('.yimg.jp') and parsed.path.endswith('/default.jpg'):
        return ''
    return url or ''


def prepare_article(article):
    item = dict(article)
    description = (item.get('description') or '').strip()
    # Keep the source unchanged for matching and grounding. Display a separate excerpt.
    end = max(description.rfind('。'), description.rfind('！'), description.rfind('？'))
    item['description_excerpt'] = description[:end + 1] if end >= 0 else ''
    item['description_incomplete'] = bool(description[end + 1:].strip()) if end >= 0 else bool(description)
    item['image'] = usable_image(item.get('image'))
    from watch_points import validate_watch
    item['watch_point'] = validate_watch(item.get('watch_point'), description)
    item['display_title'] = re.sub(r'[（(][^（）()]{1,40}[）)]$', '', item['title']).strip()
    quiz = quiz_for_article(item)
    item['quiz'] = quiz
    item['quiz_country'] = quiz['code'] if quiz else None
    from term_quizzes import term_quiz_for_article
    item['term_quiz'] = None if quiz else term_quiz_for_article(item)
    if not quiz and not item['term_quiz']:
        from headline_quizzes import headline_quiz_for_article
        item['term_quiz'] = headline_quiz_for_article(item)
    from wikidata_notes import notes_for_article
    item['knowledge_notes'] = notes_for_article(item)
    if item['term_quiz']:
        answer = item['term_quiz']['options'][item['term_quiz']['answer']]
        item['knowledge_notes'].sort(key=lambda n: n['term'] != answer)
    aliases = {'日本': ('日本', '小泉防衛相'), '韓国': ('韓国',), '中国': ('中国',),
               'アメリカ': ('アメリカ', '米国', '米軍'), 'イスラエル': ('イスラエル',),
               'イラン': ('イラン',), 'スペイン': ('スペイン',), 'フランス': ('フランス',),
               'ブラジル': ('ブラジル',), 'モンゴル': ('モンゴル',), 'フィリピン': ('フィリピン',)}
    # Quote complete source sentences; never infer diplomacy from country co-occurrence.
    item['relation_quotes'] = [s.strip() for s in re.split(r'(?<=。)', item.get('description', ''))
        if s.strip().endswith('。') and sum(any(w in s for w in words) for words in aliases.values()) >= 2]
    return item
