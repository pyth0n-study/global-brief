from dotenv import load_dotenv
import anthropic
import os

load_dotenv()
key = os.environ.get("CLAUDE_API_KEY")
print(f"APIキー先頭: {key[:20] if key else 'None'}...")

client = anthropic.Anthropic(api_key=key)

try:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": "「こんにちは」と日本語で返してください"}]
    )
    print("成功:", response.content[0].text)
except Exception as e:
    print(f"エラー: {type(e).__name__}: {e}")
