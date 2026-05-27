from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests
import anthropic
import os
import time
import sqlite3
import hashlib

load_dotenv()
API_KEY = os.environ.get("NEWS_API_KEY")
CLAUDE_KEY = os.environ.get("CLAUDE_API_KEY")

client = anthropic.Anthropic(api_key=CLAUDE_KEY)

app = Flask(__name__)
cache = {}

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


def summarize(title, content=""):
    """
    タイトル＋記事概要をClaudeへの入力として3行要約を生成する。
    contentはClaudeへのプロンプト入力にのみ使用し、そのまま表示はしない。
    """
    text_input = content if content else title
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            system=[{
                "type": "text",
                "text": (
                    "あなたは世界のニュースをわかりやすく伝える大学生です。\n"
                    "商品PR・セール・求人・プレスリリースなど報道価値のない内容なら「SKIP」とだけ返してください。\n"
                    "それ以外のニュースは、クラスの友達にLINEで教えるイメージで、必ずタメ口の3行で説明してください。\n"
                    "【口調のルール】\n"
                    "・「〜だよ」「〜なんだ」「〜みたい」「〜らしい」「〜になってる」など話し言葉を使う\n"
                    "・「〜です」「〜ます」「〜である」などの硬い表現は絶対に使わない\n"
                    "・難しい専門用語は使わず、もし使う場合はすぐ後ろに簡単な説明を添える\n"
                    "・各行は短く、テンポよく読めるようにする\n"
                    "・記号や絵文字は使わない、テキストだけで書く"
                ),
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": f"タイトル：{title}\n内容：{text_input}",
            }],
        )
        result = response.content[0].text.strip()
        if result.upper().startswith("SKIP"):
            return None
        return result
    except anthropic.APIStatusError:
        return content or title  # APIエラー時はdescriptionかタイトルで代替
    except Exception:
        return content or title


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
    url = (
        "https://newsapi.org/v2/everything"
        "?q=戦争 OR 紛争 OR 環境 OR 気候 OR 経済 OR 政治 OR 国際 OR AI OR テクノロジー OR SNS OR スポーツ OR 音楽"
        "&language=jp"
        "&pageSize=10"
        "&sortBy=publishedAt"
        f"&apiKey={API_KEY}"
    )

    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception:
        return None

    if data.get("status") != "ok":
        return None

    news = []
    for article in data.get("articles", []):
        if any(word in article["title"].lower() for word in 除外ワード):
            continue
        title = article["title"]
        source_name = article.get("source", {}).get("name") or "不明"
        article_url = article["url"]
        url_hash = hashlib.md5(article_url.encode()).hexdigest()
        if title not in cache:
            # descriptionはClaudeへの入力にのみ使用（要約生成の参考情報）
            description = article.get("description") or ""
            cache[title] = summarize(title, description)
        summary = cache[title]
        if summary is None:
            continue
        category = get_category(title)
        news.append({
            "category": category,
            "banner_color": CATEGORY_COLORS.get(category, "linear-gradient(135deg, #0d3b6e, #1a6cbd)"),
            "title": title,
            "content": summary,
            "url": article_url,
            "source": source_name,
            "url_hash": url_hash,
        })
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
