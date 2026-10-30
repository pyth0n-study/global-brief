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


def quiz_for_article(article):
    # Headline only: a dateline in the description need not be the subject country.
    title = article.get('title', '')
    def country_mention(word):
        if word == 'マリ':
            # Avoid incidental substrings: ソマリア / マリーナ / マリオ, etc.
            return re.search(r'(?<![ァ-ヺー])マリ(?![ァ-ヺー])', title)
        return re.search(re.escape(word), title)
    matches = [(match.start(), row) for row in COUNTRIES for word in row[2]
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
    item['display_title'] = re.sub(r'[（(][^（）()]{1,40}[）)]$', '', item['title']).strip()
    quiz = quiz_for_article(item)
    item['quiz'] = quiz
    item['quiz_country'] = quiz['code'] if quiz else None
    aliases = {'日本': ('日本', '小泉防衛相'), '韓国': ('韓国',), '中国': ('中国',),
               'アメリカ': ('アメリカ', '米国', '米軍'), 'イスラエル': ('イスラエル',),
               'イラン': ('イラン',), 'スペイン': ('スペイン',), 'フランス': ('フランス',),
               'ブラジル': ('ブラジル',), 'モンゴル': ('モンゴル',), 'フィリピン': ('フィリピン',)}
    # Quote complete source sentences; never infer diplomacy from country co-occurrence.
    item['relation_quotes'] = [s.strip() for s in re.split(r'(?<=。)', item.get('description', ''))
        if s.strip().endswith('。') and sum(any(w in s for w in words) for words in aliases.values()) >= 2]
    return item
