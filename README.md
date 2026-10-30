# Global Brief

国際ニュースを画像中心の縦スクロール、地図クイズ、出典付き年表で理解する、学術・非商用のWebアプリです。

公開URL：https://global-brief-00i2.onrender.com/

## 主な画面

- `/`・`/play`：縦型カード。見出しから同じカード内で説明を開閉。
- `/articles`：「一覧で読む」から従来の記事一覧へ。保存・共有・ダークモードに対応。
- `/about`：情報源、取得日、判定方法と制約。
- 画像がない・読み込めない場合は、国を特定できる記事で地図クイズを表示。
- 対応する国と話題のある記事だけ、出典付き年表と日本との接点を表示。

## 公開版のデータ

2026年10月29日に取得した記事10件と公式背景資料2件を `data/submission_news.json` に保存しています。最新ニュース配信ではありません。閲覧時にNewsData.ioやGeminiを呼び出さず、APIキーなしでも動作します。外部画像の読み込みと元記事の閲覧には通信が必要です。

途中で切れた説明文は完結した文までを表示し、元記事へ案内します。原文は照合用に保持します。要約と「ここに注目」は保存済み生成結果がある場合だけ表示します。現在の収録記事にはAI生成結果はありません。地図判定はルール方式で、未知の国を推測しません。年表・接点は出典付きデータを関連付けています。

記事・写真の出典と元記事へのリンクを各カードに表示します。画像は外部URL参照で同梱していません。地図データはNatural Earthです（static/WORLD_MAP_CREDITS.md）。プロジェクト終了後は保存記事と公開環境上のコピーを削除してください。

## 起動

Python環境で `pip install -r requirements.txt`。

ローカル：`python -m flask --app app run --host 0.0.0.0 --port 5058`

Render：Procfileの `gunicorn --timeout 180 --workers 1 --preload app:app` を使用。APIキーは公開版の表示には不要です。`ENABLE_LEGACY_APP` と `ENABLE_DEBUG_ROUTES` は設定しないでください。無料環境では初回起動に時間がかかる場合があります。

既存のAPI取得・Gemini処理はapp.pyに残していますが、既定の公開経路からは実行しません。デバッグURL・投稿APIは既定で非公開です。キーは環境変数または.envで管理し、Gitには含めません。

## 構成と検証

Python / Flask / Jinja2 / JavaScript / CSS。従来機能はSQLiteを利用し、公開版の記事はJSONで保存します。

`python -m unittest test_submission test_article_presentation test_grounded_focus test_japan_connections test_timeline_library test_news_sources test_trends`

## 背景を知る・記事アーカイブ

`/background` は、出典付きの基本解説と取得記事の記録を分けたスペースです。国・テーマで絞り込みできます。タイトルの明示的な対応語で分類し、出来事同士の因果関係や歴史を自動生成しません。

元記事URLを一意キーにSQLiteで保存し、同じ記事を再取得しても最初の保存日時を維持します。配信日時が取得できない記事には、その旨を明示します。公開画面の表示だけでは外部APIを呼ばず、現時点では保存済み10記事を初期収録します。背景資料2件はニュースの記録から除外します。

既存の `fetch_news()` は取得直後に原文を保存します。取得処理だけ試す場合は `python manage_archive.py fetch`（NewsData.ioの最大2ページを消費、AI呼び出しなし）。自動実行や定期取得はまだ有効にしていません。

`NEWS_ARCHIVE_DB` でSQLiteの保存先を指定できます。既定は `instance/news_archive.db`。ローカルではファイルを保持できますが、Renderの一時ファイルシステムでは再起動・再デプロイにより追加分が失われる場合があります。長期運用には永続ディスク等を接続し、この環境変数をそのパスに設定する必要があります（有料サービスの契約は実施していません）。

バックアップ：`python manage_archive.py export --file data/archive_export.json`
復元：`python manage_archive.py import --file data/archive_export.json`

公開URLから取得・編集・バックアップを実行する機能は設けていません。保存記事はプロジェクト終了時にバックアップと公開環境のコピーを含めて削除してください。
