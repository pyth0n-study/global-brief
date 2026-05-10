from flask import Flask, render_template
from dotenv import load_dotenv
import requests
import anthropic
import os
import time

load_dotenv()
API_KEY = os.environ.get("NEWS_API_KEY")
CLAUDE_KEY = os.environ.get("CLAUDE_API_KEY")

client = anthropic.Anthropic(api_key=CLAUDE_KEY)

app = Flask(__name__)
cache = {}

news_cache = []
news_cache_time = 0
CACHE_TTL = 1800  # 30分（秒）

def get_category(title):
    title = title.lower()
    if any(word in title for word in ["戦争", "紛争", "攻撃", "ミサイル", "軍", "イラン", "ロシア", "ウクライナ", "パレスチナ", "停戦"]):
        return "🔴 紛争・戦争"
    elif any(word in title for word in ["環境", "気候", "温暖化", "co2", "カーボン", "sdgs", "再生可能"]):
        return "🌱 環境・SDGs"
    elif any(word in title for word in ["経済", "株", "円", "gdp", "物価", "貿易", "関税"]):
        return "💰 経済"
    elif any(word in title for word in ["政治", "選挙", "首相", "大統領", "政府", "国会"]):
        return "🏛️ 政治"
    else:
        return "🌍 国際"

def summarize(title, content):
    if not content:
        return ""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            system=[{
                "type": "text",
                "text": (
                    "あなたはニュース要約アシスタントです。"
                    "必ず3行で要約してください。"
                    "世界情勢に詳しくない日本の大学生が一瞬で理解できるよう、"
                    "難しい専門用語は使わず、友達に話すような自然な言葉で書いてください。"
                ),
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": f"タイトル：{title}\n内容：{content}",
            }],
        )
        return response.content[0].text
    except anthropic.APIStatusError:
        return content or ""
    except Exception:
        return content or ""

除外ワード = ["プレスリリース", "レンタル", "オープン", "セール", "キャンペーン", "レシピ", "prtimes"]

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
        if not article.get("urlToImage"):
            continue
        if any(word in article["title"].lower() for word in 除外ワード):
            continue
        title = article["title"]
        if title not in cache:
            text = article.get("description") or title
            cache[title] = summarize(title, text)
        news.append({
            "category": get_category(title),
            "title": title,
            "content": cache[title],
            "url": article["url"],
            "image": article.get("urlToImage", ""),
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

if __name__ == "__main__":
    app.run(debug=True)
