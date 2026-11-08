"""Small, verified local flag illustrations for the optional preview."""
FLAGS = {
 'POL': ('ポーランド', '0 0 8 5', '<path fill="#fff" d="M0 0h8v2.5H0z"/><path fill="#dc143c" d="M0 2.5h8V5H0z"/>', '上が白、下が赤の2本の横帯です。', 'https://www.gov.pl/web/diplomacy/polands-day-of-the-flag'),
 'DEU': ('ドイツ', '0 0 5 3', '<path fill="#000" d="M0 0h5v1H0z"/><path fill="#d00" d="M0 1h5v1H0z"/><path fill="#ffce00" d="M0 2h5v1H0z"/>', '上から黒・赤・金の3本の横帯です。', 'https://www.gesetze-im-internet.de/flaggano_1996/i_.html'),
 'FRA': ('フランス', '0 0 3 2', '<path fill="#000091" d="M0 0h1v2H0z"/><path fill="#fff" d="M1 0h1v2H1z"/><path fill="#e1000f" d="M2 0h1v2H2z"/>', '左から青・白・赤の3本の縦帯です。', 'https://www.elysee.fr/la-presidence/le-drapeau-francais'),
}


def flag_quiz(code):
    if code not in FLAGS: return None
    name, viewbox, drawing, explanation, source = FLAGS[code]
    options = [v[0] for v in FLAGS.values()]
    return dict(kind='flag', term=name, question='この国旗の国は？', options=options,
                answer=options.index(name), explanation=explanation, source='国旗の出典：政府公式資料', url=source,
                flag_svg=f'<svg viewBox="{viewbox}" role="img" aria-label="クイズの国旗">{drawing}</svg>')
