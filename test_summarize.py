from dotenv import load_dotenv
import anthropic
import os

load_dotenv()
key = os.environ.get("CLAUDE_API_KEY")
client = anthropic.Anthropic(api_key=key)

SYSTEM_PROMPT = (
    "あなたは世界のニュースをわかりやすく伝える大学生です。\n"
    "商品PR・セール・求人・プレスリリースなど報道価値のない内容なら「SKIP」とだけ返してください。\n"
    "それ以外のニュースは以下の形式で返してください：\n\n"
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

title   = "日銀が政策金利を引き上げ、円高進む"
content = "日本銀行は本日の金融政策決定会合で政策金利を0.5%引き上げることを決定した。この決定を受けて円相場は一時1ドル140円台まで上昇した。"

print(f"テスト記事: {title}\n")

try:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=420,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": f"タイトル：{title}\n内容：{content}",
        }],
    )
    result = response.content[0].text.strip()
    print("=== Claudeの応答 ===")
    print(result)
    print("===================")

except Exception as e:
    print(f"エラー: {type(e).__name__}: {e}")
