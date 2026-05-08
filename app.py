from flask import Flask, render_template
from dotenv import load_dotenv
import requests
import os

load_dotenv()
API_KEY = os.environ.get("NEWS_API_KEY")

app = Flask(__name__)

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

除外ワード = ["プレスリリース", "レンタル", "オープン", "セール", "キャンペーン", "レシピ", "prtimes"]

@app.route("/")
def index():
    url = (
        "https://newsapi.org/v2/everything"
        "?q=戦争 OR 紛争 OR 環境 OR 気候 OR 経済 OR 政治 OR 外交 OR 国際 OR 安全保障"
        "&language=jp"
        "&pageSize=10"
        "&sortBy=publishedAt"
        f"&apiKey={API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    news = []
    for article in data["articles"]:
        if not article.get("urlToImage"):
            continue
        if any(word in article["title"].lower() for word in 除外ワード):
            continue
        news.append({
            "category": get_category(article["title"]),
            "title": article["title"],
            "content": article["description"],
            "url": article["url"],
            "image": article.get("urlToImage", ""),
        })

    return render_template("index.html", news=news)

if __name__ == "__main__":
    app.run(debug=True)