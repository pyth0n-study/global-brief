"""手動選定したイメージ写真。利用条件・出典は THUMBNAIL_CREDITS.md。"""
PHOTOS = {
    'ocean': ('https://images.unsplash.com/photo-1497044793173-df560dfbe923?auto=format&fit=crop&w=1000&q=80', 'Jeremy Bishop', 'https://unsplash.com/@jeremybishop'),
    'space': ('https://images.unsplash.com/photo-1444703686981-a3abbc4d4fe3?auto=format&fit=crop&w=1000&q=80', 'Greg Rakozy', 'https://unsplash.com/@grakozy'),
}


def curated_photo(title):
    # 無関係な写真を付けないよう、明確なテーマにだけ適用する。
    if any(word in title for word in ('宇宙', '望遠鏡', '天体', '銀河')):
        return PHOTOS['space']
    if any(word in title for word in ('海洋', '海の', '海岸', '海水', '海ごみ')):
        return PHOTOS['ocean']
    return None
