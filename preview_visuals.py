"""Source-text-only fallback graphics. No inferred causal relationships."""
from html import escape
from pathlib import Path
from functools import lru_cache
import json

@lru_cache(maxsize=1)
def world_paths():
    return json.loads((Path(__file__).parent / 'static/world_paths.json').read_text(encoding='utf-8'))


def fallback_visual(item):
    # Illustrations describe a reading theme, never a location, result or causal claim.
    import re
    title = re.sub(r'[（(][^（）()]{1,40}[）)]$', '', item.get('title', '')).strip()
    election = any(word in title for word in ('選挙', '投票', '開票'))
    head = '<svg viewBox="0 0 1000 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="テーマのイメージ。記事の現場や事実関係を示す図ではありません">'
    head += '<defs><radialGradient id="sea"><stop stop-color="#244f62"/><stop offset="1" stop-color="#102731"/></radialGradient></defs><rect width="1000" height="600" fill="url(#sea)"/>'
    if election:
        icon = '<g fill="none" stroke="#c9dfd5" stroke-width="5" stroke-linejoin="round"><path d="M390 250h220l45 55v145H345V305z"/><path d="M345 305h310M447 278h106"/><path d="m455 175 108 25-22 92-108-25z" fill="#244651"/><path d="m466 225 15 23 39-37" stroke="#d3edb8"/></g>'
        label, point = '選挙・政治', '主張と確認された事実を分けて読む'
    else:
        icon = '<g fill="none" stroke="#c9dfd5" stroke-width="5" stroke-linejoin="round"><rect x="365" y="185" width="270" height="230" rx="12"/><path d="M400 230h200M400 270h85v95h-85zM515 275h85M515 310h85M515 345h85M400 390h200"/></g>'
        label, point = 'ニュース', '詳しい内容は元記事へ'
    return head + icon + f'<text x="500" y="500" text-anchor="middle" fill="#edf5ee" font-size="28" font-family="sans-serif">{escape(label)}</text><text x="500" y="545" text-anchor="middle" fill="#bdced0" font-size="21" font-family="sans-serif">{escape(point)}</text></svg>', 'テーマのイメージ · 現場写真や事実関係の図ではありません'
