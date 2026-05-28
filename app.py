from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests
import os
import time
import sqlite3
import hashlib
import html as _html
import re

load_dotenv()
API_KEY       = os.environ.get("NEWS_API_KEY")
CLAUDE_KEY    = os.environ.get("CLAUDE_API_KEY")
UNSPLASH_KEY  = os.environ.get("UNSPLASH_ACCESS_KEY")

client = anthropic.Anthropic(api_key=CLAUDE_KEY)

app = Flask(__name__)

# httpx/httpcore の詳細ログが日本語テキストをASCII出力しようとしてクラッシュするのを防ぐ
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

cache         = {}   # title → summary text
keyword_cache = {}   # title → unsplash keywords

news_cache = []
news_cache_time = 0
CACHE_TTL = 1800  # 30分（秒）

DATABASE = 'global_brief.db'

CATEGORY_COLORS = {
    "🔴 紛争・戦争": "linear-gradient(135deg, #1c1c1e, #3a3a3c)",
    "🌱 環境・SDGs":  "linear-gradient(135deg, #2e7d32, #43a047)",
    "💰 経済":        "linear-gradient(135deg, #1565c0, #1976d2)",
    "🏛️ 政治":       "linear-gradient(135deg, #6a1b9a, #8e24aa)",
    "🌍 国際":        "linear-gradient(135deg, #00695c, #00897b)",
}

# Unsplash: カテゴリ→検索キーワード
CATEGORY_KEYWORDS = {
    "🔴 紛争・戦争": "war conflict military",
    "🌱 環境・SDGs": "nature environment climate",
    "💰 経済":        "economy finance business",
    "🏛️ 政治":       "politics government",
    "🌍 国際":        "world city global",
}

# Unsplash画像キャッシュ（記事単位・サーバー起動中保持）
_img_cache = {}  # url_hash → (url, photographer_name, photographer_link)


def is_japanese(text: str) -> bool:
    """日本語記事の判定。
    - ひらがな・カタカナがあれば確実に日本語
    - 漢字のみでもハングルがなければ日本語と見なす（「首相訪米」等の漢字見出しを救済）
    - ハングルを含む → 韓国語として除外
    - ラテン文字のみ → 英語等として除外
    """
    has_cjk = False
    for ch in text:
        cp = ord(ch)
        if 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF:
            return True                          # ひらがな・カタカナ → 確実に日本語
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            has_cjk = True                       # 漢字あり
        if 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
            return False                         # ハングルあり → 韓国語
    return has_cjk                               # 漢字のみ（中国語の混入は許容範囲）


def clean_text(text: str) -> str:
    """NewsAPIのテキストからノイズを除去する。
    - HTMLエンティティをデコード（&amp; → & など）
    - [+1234 chars] のような切り捨て表記を除去
    - 末尾の省略記号を除去
    """
    if not text:
        return ""
    text = _html.unescape(text)                          # &amp; &quot; &#39; などをデコード
    text = re.sub(r'\[[\+\d\s]*chars?\]', '', text)     # [+1234 chars] を除去
    text = re.sub(r'\.{3,}\s*$', '', text)              # 末尾の「...」を除去
    text = re.sub(r'\s{2,}', ' ', text)                 # 連続スペースを正規化
    return text.strip()


def get_article_image(keywords, url_hash):
    """記事ごとのキーワードでUnsplash画像を取得・キャッシュ。
    キーが未設定またはAPI障害時は (None, None, None) を返す。"""
    if not UNSPLASH_KEY:
        return None, None, None

    if url_hash in _img_cache:
        return _img_cache[url_hash]

    try:
        res = requests.get(
            "https://api.unsplash.com/photos/random",
            params={
                "query":       keywords,
                "orientation": "landscape",
                "client_id":   UNSPLASH_KEY,
            },
            timeout=5,
        )
        if res.status_code == 200:
            data   = res.json()
            result = (
                data["urls"]["regular"],        # 1080px幅・高画質
                data["user"]["name"],           # 撮影者名（表示義務）
                data["user"]["links"]["html"],  # 撮影者ページ（リンク義務）
            )
            _img_cache[url_hash] = result
            return result
    except Exception:
        pass
    return None, None, None


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            url_hash TEXT PRIMARY KEY,
            count    INTEGER DEFAULT 0
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS reactions (
            url_hash TEXT NOT NULL,
            reaction TEXT NOT NULL,
            count    INTEGER DEFAULT 0,
            PRIMARY KEY (url_hash, reaction)
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash   TEXT    NOT NULL,
            nickname   TEXT    NOT NULL,
            body       TEXT    NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()
    db.close()


init_db()


def get_category(title):
    title_lower = title.lower()
    if any(word in title_lower for word in ["戦争", "紛争", "攻撃", "ミサイル", "軍", "イラン", "ロシア", "ウクライナ", "パレスチナ", "停戦"]):
        return "🔴 紛争・戦争"
    elif any(word in title_lower for word in ["環境", "気候", "温暖化", "co2", "カーボン", "sdgs", "再生可能"]):
        return "🌱 環境・SDGs"
    elif any(word in title_lower for word in ["経済", "株", "円", "gdp", "物価", "貿易", "関税"]):
        return "💰 経済"
    elif any(word in title_lower for word in ["政治", "選挙", "首相", "大統領", "政府", "国会"]):
        return "🏛️ 政治"
    else:
        return "🌍 国際"


SYSTEM_PROMPT = (
    "あなたは世界のニュースをわかりやすく伝える大学生です。\n"
    "純粋な商品広告・採用情報（求人）・セール・クーポン告知のみ「SKIP」とだけ返してください。\n"
    "ニュース・社会・経済・スポーツ・科学・文化・政治・国際に関する記事はすべて以下の形式で要約してください：\n\n"
    "1行目〜3行目：クラスの友達にLINEで教えるイメージでタメ口の3行要約\n"
    "4行目：KEYWORDS: [この記事の内容に合う英語キーワードを2〜3語]\n\n"
    "【口調のルール】\n"
    "・「〜だよ」「〜なんだ」「〜みたい」「〜らしい」など話し言葉を使う\n"
    "・「〜です」「〜ます」「〜である」などの硬い表現は絶対に使わない\n"
    "・難しい専門用語は使わず、もし使う場合はすぐ後ろに簡単な説明を添える\n"
    "・記号や絵文字は使わない\n"
    "【KEYWORDSの例】\n"
    "・「日銀が金利を引き上げ」→ KEYWORDS: japan bank interest rate\n"
    "・「ウクライナに攻撃」→ KEYWORDS: ukraine war conflict\n"
    "・「パリ五輪で金メダル」→ KEYWORDS: olympics gold medal sport"
)


def summarize(title, content=""):
    if not content:
        return content, None
    return content, None

    

            if "KEYWORDS:" in result:
                parts = result.split("KEYWORDS:")
                text = parts[0].strip()
                keywords = parts[1].strip().split("\n")[0].strip()
            else:
                text = result
                keywords = ""

            return text, keywords

        except anthropic.RateLimitError as e:
            print(f"[RateLimitError] {e}")

            if attempt == 0:
                print("10秒待機して再試行...")
                time.sleep(10)
            else:
                print("リトライ失敗")
                break

        except Exception as e:
            print(f"[Claude Error] {type(e).__name__}: {e}")
            break

    fallback = clean_text(content) or title
    print(f"[Fallback] {title}")

    return fallback, ""


除外ワード = [
    # 既存
    "プレスリリース", "レンタル", "オープン", "セール", "キャンペーン", "レシピ", "prtimes",
    # 商業・PR
    "新発売", "割引", "クーポン", "通販", "お得", "初売り", "限定価格",
    "最安値", "激安", "送料無料", "販売開始",
    # 求人・採用
    "求人", "アルバイト", "採用情報",
    # ゲーム課金・美容・占い系
    "ガチャ", "課金", "美容液", "スキンケア", "占い",
    # まとめ・ランキング系広告記事
    "おすすめ", "ランキング発表", "pr times",
]


def fetch_news():
    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "domains":        "nhk.or.jp,asahi.com,mainichi.jp,yomiuri.co.jp,nikkei.com,jiji.com,47news.jp,sankei.com,tokyo-np.co.jp",
                "excludeDomains": "prtimes.jp,atpress.ne.jp,dreamnews.jp,newscast.co.jp,prlog.jp",
                "pageSize":       100,
                "sortBy":         "publishedAt",
                "apiKey":         API_KEY,
            },
            timeout=10,
        )
        data = response.json()
    except Exception as e:
        print(f"[fetch_news error] {type(e).__name__}: {e}")
        return None

    if data.get("status") != "ok":
        return None

    news = []
    for article in data.get("articles", []):
        try:
            title = article.get("title") or ""
            if not title:
                continue
            if not is_japanese(title):
                continue
            if any(word in title.lower() for word in 除外ワード):
                continue
            source_name = article.get("source", {}).get("name") or "不明"
            article_url = article.get("url") or ""
            if not article_url:
                continue
            url_hash = hashlib.md5(article_url.encode()).hexdigest()
            description = clean_text(article.get("description") or "")
            if title not in cache or cache.get(title) in (description, title, None):
                new_summary, new_kw = summarize(title, description)
                cache[title]         = new_summary
                keyword_cache[title] = new_kw
                
            summary  = cache[title]
            keywords = keyword_cache.get(title, "")
            if summary is None:
                continue
            category = get_category(title)
            article_img = article.get("urlToImage") or ""
            if article_img and article_img.startswith("http"):
                img_url, photo_by, photo_link = article_img, None, None
            else:
                search_kw = keywords or CATEGORY_KEYWORDS.get(category, "world news")
                img_url, photo_by, photo_link = get_article_image(search_kw, url_hash)
            news.append({
                "category":     category,
                "banner_color": CATEGORY_COLORS.get(category, "linear-gradient(135deg, #0d3b6e, #1a6cbd)"),
                "title":        title,
                "content":      summary,
                "url":          article_url,
                "source":       source_name,
                "url_hash":     url_hash,
                "image":        img_url,
                "photo_by":     photo_by,
                "photo_link":   photo_link,
            })
        except Exception as e:
            print(f"[article skip] {type(e).__name__}: {e}")
    return news


@app.route("/")
def index():
    global news_cache, news_cache_time

    if time.time() - news_cache_time < CACHE_TTL:
        return render_template("index.html", news=news_cache, error=False)

    result = fetch_news()

    if result is None:
        return render_template("index.html", news=news_cache, error=True)

    news_cache = result
    news_cache_time = time.time()
    return render_template("index.html", news=news_cache, error=False)


@app.route("/debug-news")
def debug_news():
    """NewsAPI の生レスポンスと日本語フィルタ結果を確認するデバッグエンドポイント"""
    results = {}

    # everything エンドポイント
    try:
        r1 = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": "政治 OR 経済 OR 国際", "pageSize": 5, "sortBy": "publishedAt", "apiKey": API_KEY},
            timeout=10,
        )
        d1 = r1.json()
        results["everything"] = {
            "status": d1.get("status"),
            "totalResults": d1.get("totalResults"),
            "message": d1.get("message"),
            "titles": [a.get("title") for a in d1.get("articles", [])],
            "japanese_pass": [is_japanese(a.get("title") or "") for a in d1.get("articles", [])],
        }
    except Exception as e:
        results["everything"] = {"error": str(e)}

    # top-headlines エンドポイント
    try:
        r2 = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={"country": "jp", "pageSize": 5, "apiKey": API_KEY},
            timeout=10,
        )
        d2 = r2.json()
        results["top_headlines_jp"] = {
            "status": d2.get("status"),
            "totalResults": d2.get("totalResults"),
            "message": d2.get("message"),
            "titles": [a.get("title") for a in d2.get("articles", [])],
        }
    except Exception as e:
        results["top_headlines_jp"] = {"error": str(e)}

    results["news_cache_count"] = len(news_cache)
    return jsonify(results)


@app.route("/debug-summary")
def debug_summary():
    """Claude要約が正常に動くか確認するデバッグ用エンドポイント"""
    test_title   = "日銀が政策金利を引き上げ、円高進む"
    test_content = "日本銀行は本日の金融政策決定会合で政策金利を0.5%引き上げることを決定した。"

    # 例外を直接捕捉してエラー内容を返す
    error_info = None
    raw_response = None
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{"role": "user", "content": f"タイトル：{test_title}\n内容：{test_content}"}],
        )
        raw_response = resp.content[0].text.strip()
    except Exception as e:
        error_info = f"{type(e).__name__}: {str(e)[:300]}"

    summary, keywords = summarize(test_title, test_content)
    return jsonify({
        "error_info":       error_info,
        "raw_response":     raw_response,
        "summary":          summary,
        "keywords":         keywords,
        "claude_key_head":  (CLAUDE_KEY or "")[:20],
        "news_cache_count": len(news_cache),
    })


# ── SNS機能 API ──────────────────────────────────────────────

VALID_REACTIONS = {'heart', 'wow', 'sad', 'angry', 'think'}


@app.route('/api/reactions', methods=['POST'])
def get_reactions():
    """複数記事のリアクション数を一括取得"""
    data = request.get_json()
    hashes = data.get('hashes', [])
    db = get_db()
    result = {}
    for h in hashes:
        result[h] = {}
        for r in VALID_REACTIONS:
            row = db.execute(
                'SELECT count FROM reactions WHERE url_hash = ? AND reaction = ?',
                (h, r)
            ).fetchone()
            result[h][r] = row['count'] if row else 0
    db.close()
    return jsonify(result)


@app.route('/api/react', methods=['POST'])
def toggle_reaction():
    """リアクションのトグル（add / remove）"""
    data = request.get_json()
    url_hash = data.get('url_hash', '')
    reaction = data.get('reaction', '')
    action   = data.get('action', 'add')

    if reaction not in VALID_REACTIONS:
        return jsonify({'error': 'Invalid reaction'}), 400

    db = get_db()
    row = db.execute(
        'SELECT count FROM reactions WHERE url_hash = ? AND reaction = ?',
        (url_hash, reaction)
    ).fetchone()

    if row is None:
        count = 1 if action == 'add' else 0
        db.execute(
            'INSERT INTO reactions (url_hash, reaction, count) VALUES (?, ?, ?)',
            (url_hash, reaction, count)
        )
    else:
        count = max(0, row['count'] + (1 if action == 'add' else -1))
        db.execute(
            'UPDATE reactions SET count = ? WHERE url_hash = ? AND reaction = ?',
            (count, url_hash, reaction)
        )

    db.commit()
    db.close()
    return jsonify({'count': count})


@app.route('/api/comments/<url_hash>', methods=['GET'])
def get_comments(url_hash):
    """記事に紐づくコメント一覧を取得"""
    db = get_db()
    rows = db.execute(
        'SELECT nickname, body, created_at FROM comments WHERE url_hash = ? ORDER BY created_at ASC',
        (url_hash,)
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/comment', methods=['POST'])
def post_comment():
    """コメントを投稿"""
    data = request.get_json()
    url_hash = data.get('url_hash', '').strip()
    nickname = data.get('nickname', '').strip()
    body = data.get('body', '').strip()

    if not nickname or not body:
        return jsonify({'error': 'ニックネームとコメントは必須です'}), 400
    if len(nickname) > 50:
        return jsonify({'error': 'ニックネームは50文字以内'}), 400
    if len(body) > 500:
        return jsonify({'error': 'コメントは500文字以内'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO comments (url_hash, nickname, body) VALUES (?, ?, ?)',
        (url_hash, nickname, body)
    )
    db.commit()
    db.close()
    return jsonify({'success': True})


if __name__ == "__main__":
    app.run(debug=True)
