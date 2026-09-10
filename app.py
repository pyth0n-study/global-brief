from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests
import os
import time
import sqlite3
import hashlib
import html as _html
import re
import json
from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel

load_dotenv()
API_KEY       = os.environ.get("NEWS_API_KEY")
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY")
UNSPLASH_KEY  = os.environ.get("UNSPLASH_ACCESS_KEY")

# 要約・INSIGHT生成にはGemini APIの無料枠を利用（従量課金のClaude APIの代替）
client = genai.Client(api_key=GEMINI_KEY)
GEMINI_MODEL = "gemini-flash-latest"  # Googleが自動追従させる最新Flashモデルのエイリアス

app = Flask(__name__)

# httpx/httpcore の詳細ログが日本語テキストをASCII出力しようとしてクラッシュするのを防ぐ
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

cache         = {}   # title → summary text
keyword_cache = {}   # title → unsplash keywords
insight_cache = {}   # title → AIによる今後の展望・押さえておきたいポイント
is_world_cache = {}  # title → 海外にも関係する話題か（false=国内限定）。フォールバック時はTrue扱い

news_cache = []
news_cache_time = 0
trends_cache = []  # サイト全体の記事を踏まえたAIによる今後の動向予測（3件程度）
CACHE_TTL = 5400  # 90分（秒）※バッチ化後も1日20リクエストの無料枠に収まるよう更新頻度を抑える（24h稼働で最大16回/日）

DATABASE = 'global_brief.db'

CATEGORY_COLORS = {
    "🔴 紛争・戦争": "linear-gradient(135deg, #1c1c1e, #3a3a3c)",
    "🌱 環境・SDGs":  "linear-gradient(135deg, #2e7d32, #43a047)",
    "💰 経済":        "linear-gradient(135deg, #1565c0, #1976d2)",
    "🏛️ 政治":       "linear-gradient(135deg, #6a1b9a, #8e24aa)",
    "🌍 国際":        "linear-gradient(135deg, #00695c, #00897b)",
    "🏠 国内":        "linear-gradient(135deg, #616161, #9e9e9e)",
}

# Unsplash: カテゴリ→検索キーワード
CATEGORY_KEYWORDS = {
    "🔴 紛争・戦争": "war conflict military",
    "🌱 環境・SDGs": "nature environment climate",
    "💰 経済":        "economy finance business",
    "🏛️ 政治":       "politics government",
    "🌍 国際":        "world city global",
    "🏠 国内":        "japan city street",
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
    db.execute('''
        CREATE TABLE IF NOT EXISTS app_state (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    db.commit()
    db.close()


def save_cache_state():
    """news_cache/trends_cacheをDBに保存する。
    プロセス再起動やGemini側の一時的な障害（503等）でtrends生成に失敗しても、
    直前まで表示できていた動向予測・ニュース一覧が消えないようにするための永続化。"""
    try:
        db = get_db()
        db.execute(
            'INSERT INTO app_state (key, value) VALUES (?, ?) '
            'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
            ('cache', json.dumps({
                'news_cache':      news_cache,
                'news_cache_time': news_cache_time,
                'trends_cache':    trends_cache,
            }, ensure_ascii=False))
        )
        db.commit()
        db.close()
    except Exception as e:
        print(f"[save_cache_state error] {type(e).__name__}: {e}")


def load_cache_state():
    """起動時にDBから前回のnews_cache/trends_cacheを復元する。"""
    global news_cache, news_cache_time, trends_cache
    try:
        db = get_db()
        row = db.execute('SELECT value FROM app_state WHERE key = ?', ('cache',)).fetchone()
        db.close()
        if row:
            data = json.loads(row['value'])
            news_cache      = data.get('news_cache', [])
            news_cache_time = data.get('news_cache_time', 0)
            trends_cache    = data.get('trends_cache', [])
    except Exception as e:
        print(f"[load_cache_state error] {type(e).__name__}: {e}")


init_db()
load_cache_state()


def get_category(title, is_world=True):
    """記事のカテゴリを判定する。
    キーワードに一致しない場合、以前は無条件で「🌍 国際」扱いだったが、
    国内限定の話題（is_world=False）まで国際に誤分類されてしまうバグがあったため、
    Geminiが判定した is_world を使って「🌍 国際」か「🏠 国内」かを振り分ける。
    """
    title_lower = title.lower()
    if any(word in title_lower for word in ["戦争", "紛争", "攻撃", "ミサイル", "軍", "イラン", "ロシア", "ウクライナ", "パレスチナ", "停戦"]):
        return "🔴 紛争・戦争"
    elif any(word in title_lower for word in ["環境", "気候", "温暖化", "co2", "カーボン", "sdgs", "再生可能"]):
        return "🌱 環境・SDGs"
    elif any(word in title_lower for word in ["経済", "株", "円", "gdp", "物価", "貿易", "関税"]):
        return "💰 経済"
    elif any(word in title_lower for word in ["政治", "選挙", "首相", "大統領", "政府", "国会"]):
        return "🏛️ 政治"
    elif is_world:
        return "🌍 国際"
    else:
        return "🏠 国内"


BATCH_SYSTEM_PROMPT = (
    "あなたは世界のニュースをわかりやすく伝える大学生です。\n"
    "入力はJSON配列で、各要素は {\"index\": 記事番号, \"title\": タイトル, \"content\": 本文} です。\n"
    "出力は {\"articles\": [...], \"trends\": [...]} という1つのオブジェクトにしてください。\n\n"
    "■ articles: 記事ごとに以下のフィールドを持つオブジェクトの配列。indexは入力と同じ値にしてください。\n"
    "・index: 入力と同じ記事番号\n"
    "・skip: 純粋な商品広告・採用情報（求人）・セール・クーポン告知ならtrue、それ以外のニュース・社会・経済・スポーツ・科学・文化・政治・国際記事はfalse\n"
    "・summary: skipがtrueなら空文字。falseならクラスの友達にLINEで教えるイメージのタメ口3行要約（改行区切りの1つの文字列）\n"
    "・keywords: この記事の内容に合う英語キーワードを2〜3語（例: \"japan bank interest rate\"）。skipなら空文字\n"
    "・insight: この記事を踏まえて今後どうなりそうか、または読者が押さえておくべきポイントを1〜2文・タメ口で。skipなら空文字\n"
    "・is_world: 海外の出来事・国際情勢・外交・世界経済・グローバルな環境問題など、海外にも関係する内容ならtrue。\n"
    "　日本国内限定の事件・芸能・スポーツ・グルメ・ローカルな話題ならfalse。skipならfalseでよい\n\n"
    "■ trends: 上記の記事全体（skipしたものは除く）を俯瞰して、今後起こりそうな展開・押さえておきたい流れを3つ、\n"
    "それぞれ1〜2文・タメ口の文字列としてまとめた配列。個別記事の内容の繰り返しではなく、複数記事を横断した傾向や見通しにすること。\n"
    "対象になる記事が少ない・偏っている場合は、無理に3つ作らず出せる範囲でよい。\n\n"
    "【口調のルール】\n"
    "・「〜だよ」「〜なんだ」「〜みたい」「〜らしい」など話し言葉を使う\n"
    "・「〜です」「〜ます」「〜である」などの硬い表現は絶対に使わない\n"
    "・難しい専門用語は使わず、もし使う場合はすぐ後ろに簡単な説明を添える\n"
    "・記号や絵文字は使わない\n"
    "【insightの例】\n"
    "・「日銀が金利を引き上げ」→ 金利が上がると住宅ローンとかの返済額も増えるから、家計への影響は要チェックだよ\n"
    "・「ウクライナに攻撃」→ 停戦交渉がどう動くか次第で、エネルギー価格にも響いてきそうだよ\n"
    "【trendsの例】\n"
    "・複数の記事で金利や為替の話題が出ているなら → 各国の金利政策の差が広がっていて、しばらく円安・株価の値動きが荒くなりそうだよ"
)


class _ArticleResult(BaseModel):
    index: int
    skip: bool
    summary: str
    keywords: str
    insight: str
    is_world: bool


class _BatchResult(BaseModel):
    articles: list[_ArticleResult]
    trends: list[str]


# 503（サーバー側の一時的な高負荷）時の再試行待機時間（秒）。1回目失敗→5秒待って再試行、2回目失敗→15秒待って再試行、
# 3回目も失敗したら諦めて呼び出し元に空を返す（＝生の本文にフォールバック）。面接等での動向予測(trends)の
# 表示安定性を優先し、消費リクエスト数の増加（最大1→3呼び出し/回）を許容する設定。
# 429（RESOURCE_EXHAUSTED＝1日の無料枠を使い切った状態）は数秒待っても回復しないため再試行しない。
RETRY_BACKOFFS = [5, 15]


def summarize_batch(pending, _attempt=0):
    """pending: [{"index": int, "title": str, "content": str}, ...]
    Gemini APIの無料枠は1日あたりのリクエスト数の上限が厳しいため、
    全記事の要約とサイト全体の動向予測を1回のAPI呼び出しにまとめて消費リクエスト数を最小化する。
    戻り値: ({index: (summary, keywords, insight) または None（skip記事）}, [動向予測の文字列, ...])
    呼び出し自体が失敗した場合は (空辞書, 空リスト) を返す（呼び出し元が生の本文にフォールバックする）。
    """
    if not pending:
        return {}, []
    payload = [{"index": p["index"], "title": p["title"], "content": p["content"]} for p in pending]
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=json.dumps(payload, ensure_ascii=False),
            config=genai_types.GenerateContentConfig(
                system_instruction=BATCH_SYSTEM_PROMPT,
                max_output_tokens=800 * len(payload) + 400,
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=_BatchResult,
            ),
        )
        parsed = resp.parsed
        if not parsed:
            raise ValueError(f"empty/unparsable response: {(resp.text or '')[:200]}")
        results = {}
        for item in parsed.articles:
            if item.skip:
                results[item.index] = None
            else:
                results[item.index] = (item.summary.strip(), item.keywords.strip() or None, item.insight.strip() or None, item.is_world)
        trends = [t.strip() for t in parsed.trends if t and t.strip()][:3]
        return results, trends
    except (genai.errors.ClientError, genai.errors.ServerError) as e:
        # サーバー混雑（503）はbackoffを挟んで最大2回まで再試行する。
        # 429は「1日の無料枠を使い切った」ケースがほとんどで、数秒〜数十秒待っても回復しないため再試行しない
        # （無駄なリクエストでさらに枠を消費するだけになる）。
        if e.code == 503 and _attempt < len(RETRY_BACKOFFS):
            wait = RETRY_BACKOFFS[_attempt]
            print(f"[summarize_batch retry] {e.code} received, retrying in {wait}s (attempt {_attempt + 1}/{len(RETRY_BACKOFFS)})")
            time.sleep(wait)
            return summarize_batch(pending, _attempt=_attempt + 1)
        print(f"[summarize_batch error] {type(e).__name__}: {e}")
        return {}, []
    except Exception as e:
        print(f"[summarize_batch error] {type(e).__name__}: {e}")
        return {}, []


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
                "pageSize":       20,  # 10→20。1バッチのGemini呼び出しが多少大きくなるが1日のリクエスト回数は変わらない
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

    # 1st pass: フィルタリングして、要約が未取得/古い記事だけをバッチ要約の対象にする
    filtered = []  # インデックス = バッチ要約時のindexと対応
    pending  = []
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

            idx = len(filtered)
            filtered.append({
                "title":       title,
                "source_name": source_name,
                "article_url": article_url,
                "url_hash":    url_hash,
                "description": description,
                "article":     article,
            })
            if title not in cache or cache.get(title) in (description, title, None):
                pending.append({"index": idx, "title": title, "content": description})
        except Exception as e:
            print(f"[article filter skip] {type(e).__name__}: {e}")

    # 2nd pass: 1回のAPI呼び出しでまとめて要約・KEYWORDS・INSIGHT・動向予測を取得してキャッシュに反映
    batch_results, trends = summarize_batch(pending)
    if trends:
        global trends_cache
        trends_cache = trends
    for item in pending:
        idx   = item["index"]
        title = filtered[idx]["title"]
        if idx in batch_results:
            result = batch_results[idx]
            if result is None:
                cache[title] = None  # AIが広告等と判定してSKIP
            else:
                summary, keywords, insight, is_world = result
                cache[title]         = summary
                keyword_cache[title] = keywords
                insight_cache[title] = insight
                is_world_cache[title] = is_world
        else:
            # バッチ呼び出し自体が失敗、またはこの記事の結果が返ってこなかった場合は生の本文にフォールバック
            cache[title]         = item["content"]
            keyword_cache[title] = None
            insight_cache[title] = None
            is_world_cache[title] = True  # 判定不能時は従来通り国際寄り扱い（誤って国内落ちさせない）

    # 3rd pass: キャッシュから最終的な記事一覧を組み立てる
    news = []
    for f in filtered:
        title = f["title"]
        summary = cache.get(title)
        if summary is None:
            continue
        keywords = keyword_cache.get(title, "")
        insight  = insight_cache.get(title, "")
        is_world = is_world_cache.get(title, True)
        category = get_category(title, is_world)
        article_img = f["article"].get("urlToImage") or ""
        if article_img and article_img.startswith("http"):
            img_url, photo_by, photo_link = article_img, None, None
        else:
            search_kw = keywords or CATEGORY_KEYWORDS.get(category, "world news")
            img_url, photo_by, photo_link = get_article_image(search_kw, f["url_hash"])
        news.append({
            "category":     category,
            "banner_color": CATEGORY_COLORS.get(category, "linear-gradient(135deg, #0d3b6e, #1a6cbd)"),
            "title":        title,
            "content":      summary,
            "url":          f["article_url"],
            "source":       f["source_name"],
            "url_hash":     f["url_hash"],
            "image":        img_url,
            "photo_by":     photo_by,
            "photo_link":   photo_link,
            "insight":      insight,
            "is_world":     is_world,
        })
    # 「Global Brief」という趣旨に沿うよう、国際ニュースを前方・国内限定ニュースを後方に回す。
    # 以前は category=="🏠 国内" で判定していたが、経済・政治などのキーワードに一致した記事は
    # 国内限定でも別カテゴリにラベル付けされて後方に回らず、国内ニュースが埋もれない原因になっていた。
    # AIが判定した is_world（記事の内容そのものの国際性）で並び替えることで正しく国際ニュースを優先する。
    # 除外はせず全件表示したまま並び順だけ調整する（安定ソートなので同カテゴリ内の順序は保たれる）
    news.sort(key=lambda item: not item["is_world"])
    return news


@app.route("/")
def index():
    global news_cache, news_cache_time

    if time.time() - news_cache_time < CACHE_TTL:
        return render_template("index.html", news=news_cache, error=False, trends=trends_cache)

    result = fetch_news()

    if result is None:
        return render_template("index.html", news=news_cache, error=True, trends=trends_cache)

    news_cache = result
    news_cache_time = time.time()
    save_cache_state()
    return render_template("index.html", news=news_cache, error=False, trends=trends_cache)


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
    """Geminiバッチ要約が正常に動くか確認するデバッグ用エンドポイント"""
    test_title   = "日銀が政策金利を引き上げ、円高進む"
    test_content = "日本銀行は本日の金融政策決定会合で政策金利を0.5%引き上げることを決定した。"

    result, trends = summarize_batch([{"index": 0, "title": test_title, "content": test_content}])
    entry  = result.get(0)
    summary, keywords, insight, is_world = entry if entry else (None, None, None, None)

    return jsonify({
        "batch_result_raw": {k: (v if v is None else list(v)) for k, v in result.items()},
        "summary":          summary,
        "keywords":         keywords,
        "insight":          insight,
        "is_world":         is_world,
        "trends":           trends,
        "gemini_key_head":  (GEMINI_KEY or "")[:12],
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
