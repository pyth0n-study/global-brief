"""Bundled, ISO-matched flag quizzes; no runtime network or AI calls."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import uuid
import xml.etree.ElementTree as ET

DIRECTORY = Path(__file__).parent / 'static/flags'
FLAGS = json.loads((DIRECTORY / 'manifest.json').read_text(encoding='utf-8'))
ET.register_namespace('', 'http://www.w3.org/2000/svg')
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
TAGS = {'svg', 'path', 'g', 'use', 'defs', 'circle', 'clipPath', 'ellipse', 'marker'}
ATTRIBUTES = {'clip-path','cx','cy','d','fill','fill-opacity','fill-rule','height','id','marker-mid',
    'markerHeight','markerWidth','r','rx','ry','stroke','stroke-linecap','stroke-linejoin',
    'stroke-miterlimit','stroke-opacity','stroke-width','transform','viewBox','width','y',
    '{http://www.w3.org/1999/xlink}href'}
EXPLANATIONS = {'POL':'上が白、下が赤の2本の横帯です。', 'DEU':'上から黒・赤・金の3本の横帯です。',
                'FRA':'左から青・白・赤の3本の縦帯です。'}


@lru_cache(maxsize=64)
def validated_svg(code):
    if code not in FLAGS: return None
    try:
        raw = (DIRECTORY / FLAGS[code]['file']).read_text(encoding='utf-8')
        if len(raw) > 100000 or '<!' in raw: return None
        root = ET.fromstring(raw)
        ids = {e.get('id') for e in root.iter() if e.get('id')}
        for e in root.iter():
            if e.tag not in {'{http://www.w3.org/2000/svg}' + t for t in TAGS}: return None
            if any(k not in ATTRIBUTES for k in e.attrib): return None
            for k, v in e.attrib.items():
                if k.endswith('href') and (not v.startswith('#') or v[1:] not in ids): return None
                if 'url(' in v and not re.fullmatch(r'url\(#[A-Za-z0-9_-]+\)', v): return None
        return raw
    except (OSError, ValueError, ET.ParseError): return None


def flag_quiz(code):
    raw = validated_svg(code)
    if raw is None: return None
    from article_presentation import COUNTRIES
    name = FLAGS[code]['name']
    row = next((r for r in COUNTRIES if r[1] == code), None)
    if row is None or row[0] != name: return None
    # Neighboring names make useful distractors; always keep exactly three choices.
    wrong = [n for n in row[3] if n != name]
    wrong += [v['name'] for v in FLAGS.values() if v['name'] != name and v['name'] not in wrong]
    answer = int(hashlib.sha256(code.encode()).hexdigest()[:8], 16) % 3
    options = wrong[:2]
    options.insert(answer, name)
    root = ET.fromstring(raw)
    prefix = 'flag-' + uuid.uuid4().hex + '-'
    ids = {e.get('id'): prefix + e.get('id') for e in root.iter() if e.get('id')}
    for e in root.iter():
        for k, v in list(e.attrib.items()):
            if k == 'id': e.set(k, ids[v])
            elif k.endswith('href'): e.set(k, '#' + ids[v[1:]])
            elif v.startswith('url(#'): e.set(k, 'url(#' + ids[v[5:-1]] + ')')
    root.set('role', 'img'); root.set('aria-label', 'クイズの国旗')
    return dict(kind='flag', term=name, question='この国旗の国は？', options=options, answer=answer,
                explanation=EXPLANATIONS.get(code, name + 'の国旗です。'), source='国旗の図柄：flag-icons（MIT）',
                url=FLAGS[code]['source'], flag_svg=ET.tostring(root, encoding='unicode'))
