"""Source-text-only fallback graphics. No inferred causal relationships."""
from html import escape
from pathlib import Path
from functools import lru_cache
import json

COUNTRY_CODES = {'ブラジル': 'BRA', 'フランス': 'FRA', '中国': 'CHN',
                 'モンゴル': 'MNG', 'イラン': 'IRN', '米国': 'USA', '日本': 'JPN'}


@lru_cache(maxsize=1)
def world_paths():
    return json.loads((Path(__file__).parent / 'static/world_paths.json').read_text(encoding='utf-8'))

PLACES = [
    ('ブラジル', -51, -14, ('ブラジル',)),
    ('フランス', 2, 47, ('フランス', '仏極右', 'ルペン')),
    ('中国', 104, 35, ('中国',)),
    ('モンゴル', 103, 47, ('モンゴル',)),
    ('イラン', 54, 32, ('イラン',)),
    ('米国', -98, 39, ('アメリカ', '米軍', '米関係', '米国', 'トランプ', 'カリフォルニア')),
    ('日本', 138, 36, ('日本', '沖縄', '嘉手納')),
]


def fallback_visual(item):
    text = item['title'] + ' ' + item.get('description', '')
    places = [(name, lon, lat) for name, lon, lat, words in PLACES if any(w in text for w in words)]
    head = '<svg viewBox="0 0 1000 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="記事に登場する国の位置模式図">'
    head += '<defs><radialGradient id="sea"><stop stop-color="#244f62"/><stop offset="1" stop-color="#102731"/></radialGradient></defs><rect width="1000" height="600" fill="url(#sea)"/>'
    if places:
        for x in range(60, 941, 110):
            head += f'<path d="M{x} 100V500" stroke="#7398a2" opacity=".18"/>'
        for y in range(100, 501, 80):
            head += f'<path d="M60 {y}H940" stroke="#7398a2" opacity=".18"/>'
        head += '<path d="M60 300H940" stroke="#9cb9bd" opacity=".3" stroke-dasharray="5 8"/>'
        selected = {COUNTRY_CODES[name] for name, _, _ in places}
        for country in world_paths():
            active = country['code'] in selected
            fill = '#b9df8b' if active else '#345764'
            stroke = '#edffcd' if active else '#77919a'
            head += f'<path d="{country["path"]}" fill="{fill}" stroke="{stroke}" stroke-width="{1.1 if active else .55}" stroke-linejoin="round"/>'
        used = []
        for name, lon, lat in places:
            x = 60 + (lon + 180) / 360 * 880
            y = 100 + (90-lat) / 180 * 400
            label_y = y - 32
            while any(abs(x-u)<100 and abs(label_y-v)<35 for u,v in used):
                label_y -= 40
            used.append((x, label_y))
            head += f'<circle cx="{x}" cy="{y}" r="7" fill="#fff7da" stroke="#183135" stroke-width="2"/><path d="M{x} {y-9}V{label_y+8}" stroke="#fff7da" stroke-width="2"/><text x="{x}" y="{label_y}" fill="#fffbe7" stroke="#102731" stroke-width="5" paint-order="stroke" font-weight="bold" font-size="25" text-anchor="middle" font-family="sans-serif">{escape(name)}</text>'
        return head + '</svg>', '登場国を強調 · 地図：Natural Earth'
    words = [w for w in ('AI', '雇用', '資源', '輸出', '選挙', '経済', 'エネルギー') if w in text][:3] or ['世界', 'ニュース']
    for index, word in enumerate(words):
        x = 500 + (index-(len(words)-1)/2)*240
        head += f'<circle cx="{x}" cy="260" r="96" fill="#ffffff09" stroke="#b4d795"/><text x="{x}" y="270" fill="#e3f5d5" text-anchor="middle" font-family="sans-serif" font-size="30">{escape(word)}</text>'
    return head + '</svg>', '記事の関連語 · 模式図'
