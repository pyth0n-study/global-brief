# Global Brief — 開発引き継ぎメモ（HANDOFF）

作成日: 2026-09-17
作成者: Claude Code（コードとローカル環境を実際に確認した上で記載）

## 表記ルール

このドキュメントでは以下を区別して書く。

- **［確認済み］** コード・git履歴・ローカルでの実行結果など、実際に確認した事実
- **［推測］** コードからは断定できない、状況からの推測（Render側の設定など、リポジトリの外にあり確認できないものを含む）

---

## 1. アプリの目的と現在の機能

**目的**［確認済み・README.mdより］
世界のニュースを短時間で把握できることを目指したAI要約ニュースWebアプリ。NewsAPIで取得した記事をAIで3行に要約し、ニュースに苦手意識がある学生でも世界情勢に触れやすくすることを狙っている。開発者本人が大学の講義がきっかけで着想し、企画・設計・実装・デプロイを個人で行った、という経緯がREADMEに書かれている。

**現在の機能**［確認済み・app.py / templates/index.html / static/main.jsより］

- NewsAPIから日本語ニュースを取得（`domains`指定・`pageSize=20`・`sortBy=publishedAt`）
- AI（Gemini）による記事の3行要約（タメ口・話し言葉スタイル）
- AIによる「これからどうなる？」insight（記事ごとの一言展望）
- AIによるサイト全体の「今後の動向予測」（trends、最大3件、トップに表示）
- カテゴリ自動分類（紛争・戦争／環境・SDGs／経済／政治／国際／国内）。キーワード一致 + AI判定の `is_world` フラグを併用
- 国際ニュースを優先、国内限定ニュースを後方に並び替え
- 広告・求人・セール等をタイトルの除外ワードで一次フィルタ、AIでも二次判定してスキップ
- 記事画像がない場合、AIが出したキーワードでUnsplashから画像取得（取得失敗時はカテゴリ別グラデーションバナーにフォールバック）
- リアクション（5種類）、ニックネームコメント、ブラウザへのブックマーク保存（localStorage）、X/LINE/URLコピー共有
- ダークモード、レスポンシブ表示
- 単語ダブルクリックでのGoogle検索（PCのみ、README記載の既知の制約としてスマホ非対応）
- ニュース一覧・動向予測はサーバー側でキャッシュ（後述）し、SQLiteに永続化

---

## 2. 技術スタックと主要ファイルの役割

**技術スタック**［確認済み］

- Python 3（ローカル動作確認環境: Python 3.14.4）
- Flask 3.1.3
- google-genai 2.0.1（Gemini API SDK。`pydantic` 2.13.4 に依存、要約結果のスキーマ検証に使用）
- requests 2.33.1（NewsAPI / Unsplash 呼び出し）
- python-dotenv（`.env` 読み込み）
- gunicorn 26.0.0（本番サーバー）
- SQLite（`global_brief.db`、標準ライブラリ `sqlite3` 経由）
- フロントは素のHTML/CSS/JS（フレームワークなし、Jinja2テンプレート）

⚠️ **README.mdの「技術構成」欄はClaude APIのまま古い記述になっている**［確認済み］。実際は後述の通りGemini APIに切り替わっている。就活資料として見られる可能性があるため、事実に合わせて更新が必要。

**主要ファイル**［確認済み］

| ファイル | 役割 |
|---|---|
| `app.py`（649行） | 全ロジック。NewsAPI取得、AI要約・動向予測、カテゴリ分類、DB永続化、SNS機能API、Flaskルーティング |
| `templates/index.html`（173行） | メインページのJinja2テンプレート。ニュースカード、trendsセクション、サイドバー、コメント欄のHTML構造 |
| `static/style.css`（659行） | 全スタイル（ダークモード、レスポンシブ含む） |
| `static/main.js`（296行） | クライアント側の挙動（リアクション/コメントのfetch呼び出し、ブックマークのlocalStorage管理、ダークモード切替、単語検索ツールチップ、シェア機能） |
| `global_brief.db` | SQLite本体。`.gitignore`対象なので**リポジトリには含まれない**。ローカル・Render双方でapp.py実行時に`init_db()`が自動生成 |
| `requirements.txt` | 依存パッケージ一覧（**バージョン固定なし**、後述） |
| `Procfile` | `web: gunicorn --timeout 180 --workers 1 --preload app:app` |
| `test_claude.py` / `test_summarize.py` | **旧Claude API時代の動作確認スクリプト。現在のapp.pyからは呼ばれておらず、実質デッドコード**［確認済み・grep結果］。`CLAUDE_API_KEY`を読むため、放置すると次の開発者が「Claude APIがまだ使われている」と誤解する原因になり得る |
| `.env` | 環境変数（`.gitignore`対象、リポジトリには含まれない） |

---

## 3. 依存関係のインストール方法と起動方法

［確認済み・README.md記載の手順、内容は現状と整合性あり］

```bash
git clone https://github.com/pyth0n-study/global-brief.git
cd global-brief
python -m venv .venv
```

Windows:
```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

プロジェクト直下に `.env` を作成（値は各自のAPIキーに置き換え。詳細は5節）:
```env
NEWS_API_KEY=
GEMINI_API_KEY=
UNSPLASH_ACCESS_KEY=
```

起動:
```bash
python app.py
```
`http://127.0.0.1:5000` で確認。`app.run(debug=True)` のため開発サーバーで起動する（app.py:648-649）。

⚠️ **README.mdの`.env`例は`CLAUDE_API_KEY`のままで`GEMINI_API_KEY`の記載がない**［確認済み］。このままだと新しく環境構築する人がGEMINI_API_KEYの設定漏れに気づけない。要更新。

⚠️ `requirements.txt` にバージョン指定が一切ない［確認済み・requirements.txt全文6行、すべてパッケージ名のみ］。また `app.py` が直接importしている `pydantic` が `requirements.txt` に明記されておらず、`google-genai` の依存として間接的に入っている状態［確認済み・`pip list`で`pydantic 2.13.4`確認、requirements.txtには記載なし］。`google-genai`側の依存が変わると再現性が崩れるリスクがある。

---

## 4. 処理の流れ（ニュース取得 → AI要約・動向予測 → DB保存 → 画面表示）

［確認済み・app.py:349-483の実装を追った内容］

1. **リクエスト受信**（`/` ルート、app.py:468）: `news_cache_time` からの経過時間が `CACHE_TTL`（5400秒＝90分、app.py:39）未満ならAPIを呼ばずキャッシュ（`news_cache`/`trends_cache`）をそのまま描画して終了。
2. **TTL超過時のみ `fetch_news()` を実行**（app.py:349-465）:
   - NewsAPI `/v2/everything` を1回呼び出し、`pageSize=20`で最新記事を取得
   - 1st pass: 日本語判定（`is_japanese`）、除外ワードフィルタ、URL欠損チェックなどでノイズを除去し `filtered` リストを作成。同時に「まだAI要約していない（or 要約結果が生本文と同一＝フォールバック状態だった）」記事だけを `pending` リストに積む（重複要約を避ける仕組み、app.py:389-399）
   - 2nd pass: `pending` をまとめて**1回のGemini API呼び出し**（`summarize_batch`、app.py:285-331）に渡し、要約・keywords・insight・is_world・サイト全体のtrendsを一括取得。結果を `cache` / `keyword_cache` / `insight_cache` / `is_world_cache`（すべてプロセス内メモリの辞書）に反映
   - 3rd pass: `filtered` とキャッシュ済み辞書から最終的な記事リスト（表示用の全フィールド）を組み立て。画像が無い記事はUnsplash APIで補完。`is_world` で国際優先に並び替え
3. **DB保存**（`save_cache_state()`、app.py:174-192）: 組み立てた `news_cache` / `news_cache_time` / `trends_cache` をJSON化してSQLiteの `app_state` テーブル（key='cache'）にUPSERT。プロセス再起動時は `load_cache_state()`（app.py:195-208）で復元。
4. **画面表示**: `render_template("index.html", news=news_cache, trends=trends_cache, error=...)` でJinja2テンプレートに渡し、カード一覧とtrendsセクションを描画。フロント側のリアクション数・ブックマークはページロード後に `main.js` が別途 `/api/reactions` 等をfetchして反映。

---

## 5. 必要な環境変数の名前と用途

［確認済み・app.py:16-22 および .envのキー名（値は未記載）］

| 変数名 | 用途 | 必須 |
|---|---|---|
| `NEWS_API_KEY` | NewsAPI（記事取得）の認証キー | 必須 |
| `GEMINI_API_KEY` | Gemini API（要約・insight・trends生成）の認証キー。現在AI機能の本体 | 必須 |
| `UNSPLASH_ACCESS_KEY` | Unsplash API（記事画像の補完）の認証キー | 任意（未設定時は `get_article_image` が `(None, None, None)` を返し、カテゴリ別バナーにフォールバック。app.py:103-104） |
| `CLAUDE_API_KEY` | 旧Claude API用。**現在のapp.pyでは未使用**。`.env`には存在し、`test_claude.py`/`test_summarize.py`が読むのみ | 現状は不要（デッドコード用） |

APIキーの実際の値は本ドキュメントに記載していない。`.env`は`.gitignore`済みでリポジトリには含まれない［確認済み］。

---

## 6. Renderのビルドコマンド・起動コマンド・公開手順

**リポジトリ内から確認できる情報**［確認済み］

- `render.yaml` はリポジトリに存在しない（`find`で未検出）。つまりRenderの設定はRenderダッシュボード側にのみ保存されており、**このリポジトリだけからは正確な設定値を再現できない**。
- `Procfile` は存在する: `web: gunicorn --timeout 180 --workers 1 --preload app:app`。Render/Herokuスタイルの構成では、これがそのまま起動コマンドとして使われている可能性が高い。
- README.mdには「Renderの無料プランを利用しているため、初回表示に時間がかかる場合があります」という記述があるのみで、ビルド/起動コマンドの明記はない。

**推測（Renderダッシュボードでの一般的な設定として）**［推測］

- Build Command: `pip install -r requirements.txt`（Render Python環境のデフォルト）
- Start Command: `Procfile`の内容がそのまま使われている可能性が高い（未確認）
- 環境変数（`NEWS_API_KEY` / `GEMINI_API_KEY` / `UNSPLASH_ACCESS_KEY`）はRenderのEnvironment設定画面で個別に登録されているはず（未確認）

**Codexへの引き継ぎ事項**: Renderの実際のビルド/起動コマンド・環境変数設定は、Renderダッシュボードにログインして直接確認する必要がある。今回はこの作業を行っていない。

---

## 7. 直近の変更・未完了の作業・未コミットの変更

**直近の変更**［確認済み・git log］

最新コミット `956e2a5`（2026-09-10）で、Claude APIからGemini無料枠への切り替え、`is_world`判定による国際/国内の誤分類修正、`news_cache`/`trends_cache`のSQLite永続化、503エラー時のリトライ（最大2回・backoff付き）が入った。コミットメッセージ全文はgit log参照。

**未コミットの変更**［確認済み］

`git status` は clean（`nothing to commit, working tree clean`）。現時点で未コミットの変更は無い。

**未完了の作業**［確認済み・README.md「今後の改善」チェックリストより］

- [ ] スマートフォン向け語彙検索（現在PCのみ対応）
- [ ] 表示記事数の拡充
- [ ] ユーザーが選択できるカテゴリフィルター
- [ ] AI要約の品質評価と精度向上
- [ ] リアクション・コメントデータの永続化強化（SQLiteのままで良いか含め要検討、とREADMEに明記）

このほか、README.md自体に古い記述が複数残っている（Claude API表記、`.env`例に`GEMINI_API_KEY`が無い、「表示するニュースは現在最大10件」だが実装は`pageSize=20`）ため、ドキュメント更新も未完了作業として引き継ぐ。

---

## 8. 現在の不具合と再現手順、確認済みのエラー

### 不具合①: Gemini無料枠の1日あたりリクエスト上限が非常に少なく、すぐ枯渇する

**［確認済み］** 本セッション中に、実際の`.env`の`GEMINI_API_KEY`を使って`summarize_batch`相当のAPI呼び出しをローカルから直接実行し、以下のエラーを再現した。

```
429 RESOURCE_EXHAUSTED
Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests
quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier
model: gemini-3.8-flash
quotaValue: 20
```

**再現手順**:
1. `.env`の`GEMINI_API_KEY`を読み込み、`google.genai.Client`で`generate_content`を呼ぶ（app.pyの`summarize_batch`と同じ呼び出し方）
2. その日にすでに20回分のリクエストを消費済みであれば、即座に上記429が返る

**わかったこと**:
- `app.py`で使っているモデル名は`"gemini-flash-latest"`（app.py:22）という**Googleが自動で最新Flashモデルへ追従させるエイリアス**。今回そのエイリアスの実体が`gemini-3.8-flash`であり、この実体モデルの無料枠は**1日20リクエストのみ**だった。
- `app.py`のコード内コメント（app.py:39）は「1日20リクエストの無料枠に収まるよう」90分キャッシュ(`CACHE_TTL`)を設計したとあり、Render本番稼働分（24時間で最大16回）を想定した数字にはなっている。しかし**ローカル開発でのテスト呼び出しや`/debug-summary`エンドポイントへのアクセスも同じ1つのAPIキー＝同じ20回のクォータを共有して消費する**ため、開発中の動作確認だけで簡単に枯渇し得る。
- クォータ枯渇時、`summarize_batch`は`{}, []`を返し（app.py:328）、`fetch_news()`は該当記事を生の記事本文（NewsAPIのdescription）にフォールバック表示し、`trends_cache`は更新されない（空のまま）（app.py:404-426）。**この状態はエラー表示にはならず、一見動いているように見えるが、AI要約・AI動向予測が実質機能していない状態になる。**
- ローカルのDB（`global_brief.db`）を確認したところ、`news_cache`は20件あるのに`trends_cache`は0件という状態だった。これは上記フォールバックが発生していたことと一致する。

### 不具合②（推測寄りだが根拠あり）: プロセス再起動のたびに要約済み記事が重複してAI処理される

**［確認済み・コード読解による］** `save_cache_state()`（app.py:174-192）がSQLiteに永続化しているのは`news_cache` / `news_cache_time` / `trends_cache`の3つのみ。一方、記事タイトル単位で「すでに要約済みか」を判定するための`cache` / `keyword_cache` / `insight_cache` / `is_world_cache`（app.py:31-34、いずれもプロセス内メモリの辞書）は**永続化されていない**。

`fetch_news()`の重複防止ロジック（app.py:398）は `if title not in cache or cache.get(title) in (description, title, None):` という条件で「まだ要約していない記事」を`pending`に積んでいる。プロセスが再起動すると、この`cache`辞書は空の状態からスタートするため、**直前まで正常に要約できていた記事も含めて、次のTTL到来時に全記事が再度Geminiへ送られる**（＝重複したAI処理）。

**［推測］** Renderの無料プランはアイドル時にスリープし、アクセスのたびに再起動が発生する挙動が知られている。この挙動と組み合わさると、「スリープ→再起動→全記事再要約」が繰り返され、不具合①のクォータ枯渇をさらに早める一因になっている可能性が高い。ただしRender側の実際の再起動頻度はダッシュボードのログで確認しておらず、ここは推測にとどまる。

---

## 9. 実施済みの動作確認と未確認の項目

**実施済み**［確認済み・すべて本セッション内でローカル実行して確認］

- ローカル環境で`.env`の4つのキーがすべて非空で設定されていることを確認
- `git log`でClaude→Gemini移行が入ったコミット（956e2a5）を特定
- ローカルの`global_brief.db`の`app_state`テーブルから`news_cache`（20件）・`trends_cache`（0件）の実データを確認
- `.env`の`GEMINI_API_KEY`を使い、`app.py`と同じ呼び出し方でGemini APIを実際に呼び出し、429 RESOURCE_EXHAUSTEDエラーと、そのクォータ詳細（`gemini-3.8-flash`・20リクエスト/日）を直接確認
- `pip list`相当（`python -m pip list`）でインストール済みパッケージの実バージョンを確認し、`pydantic`が`requirements.txt`に未記載であることを確認
- `git status` / `git diff --stat`で未コミットの変更が無いことを確認

**未確認（今回は意図的に行っていない）**［確認済み・指示に基づき未実施］

- Renderダッシュボード上の実際のビルド/起動コマンド・環境変数設定
- 本番（Render）環境での実際の挙動（コード変更・デプロイ・有料/従量APIの呼び出しを今回は行わない、という指示のため）
- `/api/reactions`・`/api/react`・`/api/comments`・`/api/comment`などSNS機能APIの実際の動作（コードレビューはしたが、ブラウザ経由での実クリック確認はしていない）
- `likes`テーブル（app.py:142-146で`CREATE TABLE`されているが、参照している他のコードが見つからない。使われていないテーブルの可能性がある。要調査）
- スマートフォン実機・実ブラウザでの表示確認
- Gemini無料枠の「翌日リセット後に正常に動くかどうか」の確認（今回は同日中にクォータ超過状態を再現しただけで、回復後の正常系は未確認）

---

## 10. 次に調べるべきこと

優先度が高いと考えられる順。

1. **`gemini-flash-latest`を安定版モデル名に固定し、無料枠の広いモデルへ切り替える**。`-latest`エイリアスがGoogle側の都合で無料枠の狭いモデルに自動追従してしまうのが不具合①の直接原因のため、まずここを塞がないと他の対策をしても再発する。どのモデル名が現時点で無料枠が広いかはGoogle AI Studio / Gemini APIのドキュメント・料金ページで要確認（本ドキュメント作成時点では未調査）。
2. **`cache`/`keyword_cache`/`insight_cache`/`is_world_cache`をSQLiteに永続化する**（`news_cache`/`trends_cache`と同様に）。プロセス再起動をまたいでも「この記事は要約済み」と判定できるようにし、不具合②（重複AI処理）を解消する。記事の一意キーは`url_hash`があるのでそれを使うのが自然。
3. **ローカル開発用と本番用でGemini APIキーを分離する**。同じ20回/日の枠を奪い合わないようにする。
4. **`/debug-news`・`/debug-summary`を本番で無効化 or 認証で保護する**。誰でも叩けてクォータを消費できてしまう状態になっている（app.py:486-549）。
5. **アクセス時ではなく定期実行（スケジューラ）でニュース取得・AI処理を行う構成への変更を検討する**。1日の呼び出し回数を完全に固定・予測可能にでき、「維持費を抑えたい」「同じ記事への重複処理を避けたい」という方針の両方に効く。ただし構成変更を伴うため、着手前にユーザーへの確認が必要（過去のやり取りで「API利用量に関わる変更は必ず確認してから」という方針が示されている）。
6. **Renderダッシュボードの実際の設定（ビルド/起動コマンド、環境変数、スリープ挙動）を確認する**。6節に書いた内容は推測を含むため、実際の設定値で裏取りする。
7. **README.mdの記述をコードの実態に合わせて更新する**（Claude API表記、`.env`例、表示件数など）。就活で見られる可能性がある資料のため優先度は高いが、機能修正ではないので後回しでもよい。
8. **`likes`テーブルが本当に未使用か確認し、未使用なら削除するかREADMEの制約欄と整合させる**。
9. **`requirements.txt`にバージョンを固定し、`pydantic`を明示的に追加する**。再現性の担保のため。
10. **`test_claude.py`/`test_summarize.py`の扱いを決める**（削除する、またはGemini版に書き換えて残す）。放置すると「Claude APIをまだ使っている」という誤解の元になる。

---

## 参考: このプロジェクトの今後の方針（ユーザーから伝えられている内容）

- まず不具合の原因を切り分け、安定して動く状態にしたい
- Renderと外部APIの維持費を抑えたい（無料枠の範囲内での運用を継続したい、課金は想定していない）
- 同じ記事への重複したAI処理を避けたい
- 就活用に、実装内容と自分の判断を説明できる状態にしたい（技術的な工夫を自分の言葉で語れることを重視）
