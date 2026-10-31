# 起動・データ保存・運用手順

[READMEに戻る](../README.md)

## 起動

Python環境で `pip install -r requirements.txt`。

ローカル：`python -m flask --app app run --host 0.0.0.0 --port 5058`

Render：Procfileの `gunicorn --timeout 180 --workers 1 --preload app:app` を使用。APIキーは公開版の表示には不要です。`ENABLE_LEGACY_APP` と `ENABLE_DEBUG_ROUTES` は設定しないでください。無料環境では初回起動に時間がかかる場合があります。

既存のAPI取得・Gemini処理はapp.pyに残していますが、既定の公開経路からは実行しません。デバッグURLは非公開です。一覧のリアクション・コメントAPIのみ明示的に公開しています。キーは環境変数または.envで管理し、Gitには含めません。

## 検証

`python -m unittest test_submission test_public_feed test_public_social test_news_archive test_archive_store test_article_presentation test_grounded_focus test_japan_connections test_timeline_library test_news_sources test_trends`

## 背景を知る・記事アーカイブ

`/background` は、「まず知っておきたい」と「過去のニュースを探す」のタブに分かれたスペースです。国・テーマで絞り込みできます。タイトルの明示的な対応語で分類し、出来事同士の因果関係や歴史を自動生成しません。

元記事URLを一意キーにSQLiteで保存し、同じ記事を再取得しても最初の保存日時を維持します。配信日時が取得できない記事には、その旨を明示します。公開画面の表示ではニュース・AI APIを呼ばず、初期収録の10記事に加え、定期取得した記事を読み込みます。背景資料2件はニュースの記録から除外します。

既存の `fetch_news()` は取得直後に原文を保存します。取得処理だけ試す場合は `python manage_archive.py fetch`（NewsData.ioの最大2ページを消費、AI呼び出しなし）。公開版の定期取得は、以下のGitHub Actionsで実行します。

`NEWS_ARCHIVE_DB` でSQLiteの保存先を指定できます。既定は `instance/news_archive.db`。ローカルではファイルを保持できますが、Renderの一時ファイルシステムでは再起動・再デプロイにより追加分が失われる場合があります。公開版ではGitHubの専用ブランチを永続保存元にし、SQLiteはそこから復元できる読み込み用キャッシュとして使います。Renderの有料ディスクは契約していません。

バックアップ：`python manage_archive.py export --file data/archive_export.json`
復元：`python manage_archive.py import --file data/archive_export.json`

公開URLから取得・編集・バックアップを実行する機能は設けていません。保存記事はプロジェクト終了時にバックアップと公開環境のコピーを含めて削除してください。

背景解説には、ロシア・ウクライナの独立・2014年の紛争・2022年の全面侵攻までの経緯と、確認済みの直近の動きを分けて収録しています（data/russia_ukraine_background.json）。本文ごとに出典を付け、AI・閲覧時のAPIで自動生成していません。追加・更新時には出典と確認日を見直してください。

記事の保存件数にはコード上の上限を設けていません（保存容量には依存）。画面は最新200件までを表示し、exportは全件が対象です。記事を開かなくても取得時に保存されます。本文全体・写真ファイルは保存していません。

## 無料構成での定期蓄積・復旧

- `.github/workflows/archive-news.yml`：GitHub標準Ubuntuランナー、毎日00:23/12:23 UTC（日本時間09:23/21:23）。手動実行も可能。並列実行を抑止し、10分で終了します。
- 1回NewsData.ioの最大2ページ、通常1日最大4ページ（各最大10記事）。Geminiは呼びません。取得・保存に記事の閲覧は不要。全てのニュースを取り切る保証はありません。
- `NEWSDATA_API_KEY` はGitHub Actions Secret。フォークでは実行しません。アプリの閲覧者へキーを送信しません。
- 永続保存元：同じリポジトリの **archive-data** ブランチの `archive.json`。見出し・説明文・URL・出典・配信日時・初回保存日時・提供された画像URLのみ。本文全体・写真ファイル・APIキーは保存しません。公開リポジトリなのでこのデータも公開されます。
- `/background` は5分間隔を上限に公開スナップショットを同期。Render再起動後にも復元できます。GitHubの読み込み障害時はローカルの直前データ、再起動直後なら収録10記事を表示します。トップ・一覧も同じ保存元を利用し、新しい20件までを配信日時（ない場合は初回保存日時）の順で表示します。取得前や復元できない場合は収録12カードへフォールバックします。
- バックアップは各実行のActions Artifact `news-archive-実行ID`（gzip JSON + SHA-256、7日保持）。専用ブランチのコミット履歴も残ります。別アカウント・別事業者への複製ではありません。
- 圧縮バックアップは1回5 MiB以下。1日2回×7日で約70 MiB以内に制限し、サイズ超過時は公開更新を停止して失敗にします。GitHubアカウント全体の他用途の消費量は別途確認してください。有料ランナー・有料DB・有料APIを追加していません。
- 実行失敗はActionsに表示。APIエラー・空の応答・壊れた復元データで直前の公開スナップショットを上書きしません。定期処理は遅延・スキップされる場合があり、公開リポジトリでは60日間活動がないと無効になる場合があります。Actions画面を定期的に確認してください。

### バックアップから復元

1. Actionsの成功した実行からArtifactをダウンロードし、gzipとsha256を同じフォルダーへ展開。
2. `python manage_archive.py import --file archive-backups/archive-backup.json.gz`。チェックサム不一致では復元しません。元の初回保存日時を保持し、URLで重複を防止します。
3. ローカル復旧後のJSON出力は `python archive_pipeline.py --folder archive-backups/recovered`（API不使用）。公開元の復旧はarchive-dataブランチへそのarchive.jsonをコミットし、次回の取得を実行。
4. GitHub履歴からの復旧も、過去コミットのarchive.jsonを取得し、同じimportで実行可能。

プロジェクト終了時はワークフローを無効化し、archive-dataブランチ、Actions Artifact、ローカルのDB・バックアップも削除してください。Gitの履歴・キャッシュに残ったデータの削除にはGitHub側の手続きが必要な場合があります。許可された保存期間を超えてアーカイブを継続しないでください。

定期取得記事のトップ表示では、配信元の画像URLを使用します。画像なし・読み込み失敗時は、見出しから対象国を特定できる場合に地図クイズを表示します。説明が完結した文を含む場合、見出しを押すと同じカード内で開閉できます。NewsData.io/Geminiは閲覧時に呼びません。開いた画面は自動差し替えせず、再読み込みで更新します。

## 一覧のリアクション・コメント

`/articles` で従来の共有リアクション・コメントを利用できます。JSON型・文字数・記事IDを検証し、同一送信元の連投と別オリジンの投稿を制限します。コメント表示時はHTMLエスケープします。投稿データは従来のglobal_brief.dbに保存しており、記事アーカイブのGitHubバックアップ対象には含めません。Renderの一時ディスクでは再起動・再デプロイで消える可能性がある試験運用です。ユーザー投稿をGit公開履歴へ複製しない方針です。長期保存には別途永続DBと運用整備が必要です。
