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
    # Display source words only. No guessed place, event image or explanation.
    lines = [title[i:i + 12] for i in range(0, len(title), 12)]
    size = min(36, max(14, 270 // max(1, len(lines))))
    head = '<svg viewBox="0 0 600 600" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="見出しカード">'
    head += '<defs><radialGradient id="sea"><stop stop-color="#244f62"/><stop offset="1" stop-color="#102731"/></radialGradient></defs><rect width="600" height="600" fill="url(#sea)"/>'
    head += '<path d="M45 130h45M45 130v45M555 500h-45M555 500v-45" fill="none" stroke="#bedbc5" stroke-width="2"/>'
    head += '<text x="65" y="170" fill="#b8d9d4" font-size="18" letter-spacing="4" font-family="sans-serif">GLOBAL BRIEF</text>'
    for i, line in enumerate(lines):
        head += f'<text x="65" y="{230 + i * (size + 14)}" fill="#edf5ee" font-size="{size}" font-family="sans-serif" font-weight="600">{escape(line)}</text>'
    return head + '</svg>', '記事の見出しを使ったカード · 現場写真ではありません'
