# Axiom OS 実装記録

このドキュメントは、Axiom プロジェクトで現状までに実装した内容を記録したものです。

---

## 1. プロジェクト概要

**Axiom OS** は、組織の「脳」として現場ログを収集・解析し、5つの公理（Data Integrity / Algorithmization / Execution Value / Lead Time Cost / Autonomous Evolution）に基づいて自律的な判断と指示を出力するシステムです。  
ローカル開発環境では Flask バックエンド（mock_backend）が「脳」、index.html がコマンドセンター、各種 Python スクリプトがエージェント・テストとして動作します。

---

## 2. 環境構築

- **Python:** 3.x（venv 推奨）
- **依存:** `requirements.txt` に記載
  - flask, flask-cors, pandas, requests, python-dotenv, google-generativeai
- **環境変数:** `.env` で管理（リポジトリには含めない）
  - `GEMINI_API_KEY` … Gemini API（未設定時はフォールバック動作）
  - `CENTRAL_BRAIN_URL` … 脳のエンドポイント（デフォルト: http://localhost:5001/api/logs）
  - `CHATWORK_TOKEN` … Chatwork 連携用（任意）
  - `GCHAT_SPACE_A_URL` / `GCHAT_SPACE_B_URL` … Google Chat 用（任意）

---

## 3. 実装済みファイル一覧

| ファイル | 役割 |
|----------|------|
| **mock_backend.py** | Axiom OS コアエンジン（Flask）。CORS 有効。組織コンテキストの永続化・Gemini によるログ解析・プロトコル抽出・API 提供。 |
| **index.html** | コマンドセンター UI。`/api/axiom-bi` から 10 秒ごとにデータ取得し、Total Logs / Protocols Extracted / Average Urgency、Recent Decisions、Extracted Logic (Axiom 2) を表示。 |
| **seed_context.py** | 光回線代理店情報 CSV を読み込み、`POST /api/ingest` で `agencies` カテゴリに投入。 |
| **observer_bot.py** | APCLO Eye（現場観測エージェント）。`CENTRAL_BRAIN_URL` へ観測データを POST。`observe_and_send()` で送信。 |
| **ai_orchestrator.py** | オーケストレーター。起動時に observer_bot 経由で脳へ疎通テスト送信し、待機。 |
| **sonet_auto_worker_v2_1.py** | 自律実行ワーカー（So-net 50 件制限など）のシミュレーション。実行結果を `POST /api/logs` で脳に報告。 |
| **learning_loop_test.py** | 学習ループ検証。エキスパート（田中氏）の新ルール送信 → 3 秒待機 → 新人の質問送信。回答に「Google Map」が含まれるかで Axiom 2/5 の継承を確認。 |
| **requirements.txt** | Python 依存パッケージ一覧。 |
| **.env** | 環境変数（CHATWORK_TOKEN, CENTRAL_BRAIN_URL, GCHAT_SPACE_* 等）。※ リポジトリには含めない。 |

---

## 4. mock_backend.py（Axiom OS コア）の詳細

- **永続化:** `axiom_intelligence_storage`（判断ログ）、`EXTRACTED_PROTOCOLS`（Axiom 2 で抽出したプロトコル）
- **組織コンテキスト:** `ORGANIZATIONAL_CONTEXT`（agencies / workflows / rules / experts / metadata）。`/api/ingest` で dict マージ・list 拡張・新規カテゴリ追加に対応。
- **Gemini 連携:** `analyze_with_gemini()` で直近 15 件のプロトコルとコンテキスト全文をプロンプトに注入。JSON で `aligned_axiom`, `urgency_score`, `logic_extraction`, `action_instruction`, `reasoning` を取得。
- **API:**
  - `POST /api/ingest` … コンテキスト注入（category, payload）。レスポンスに `current_categories`。
  - `POST /api/stores/upsert` … 外部連携用。payload を `agencies` として ingest。
  - `POST /api/logs` … ログ受信 → Gemini 解析 → decision をストレージに追加。Axiom 2 検知時は `EXTRACTED_PROTOCOLS` に追加。
  - `GET /api/axiom-bi` … `summary_stats`（total_logs, logic_extractions, context_categories）、`bi_ready_logs`、`new_protocols`、`raw_context_snapshot` を返却。

---

## 5. フロントエンド（index.html）

- Tailwind CSS / Chart.js（CDN）、Noto Sans JP / Inter フォント。
- `http://localhost:5001/api/axiom-bi` を 10 秒ごと + 強制更新ボタンで取得。
- 表示: Total Logs Processed、Axiom 2: Protocols Extracted、Average Urgency（bi_ready_logs から算出）、Recent Decisions（カード）、Extracted Logic（プロトコル一覧）。
- 接続失敗時はエラーメッセージ表示。XSS 対策のため `escapeHtml()` でエスケープ。

---

## 6. テスト・検証

- **learning_loop_test.py:** エキスパートの知恵が組織ルールとして AI に継承されるか（Axiom 2 & 5）を検証。田中氏の「Google Map で確認」ルール → 新人の質問に対する回答に「Google Map」が含まれるかで成功/失敗を判定。
- **sonet_auto_worker_v2_1.py:** 自律タスク完了を脳に報告する流れのシミュレーション。

---

## 7. 運用メモ

- 脳の起動: `./venv/bin/python mock_backend.py`（ポート 5001）
- コマンドセンター: ブラウザで `index.html` を開く（file:// または同一オリジンの HTTP）。CORS は mock_backend で許可済み。
- 代理店コンテキスト投入: 脳起動後に `./venv/bin/python seed_context.py`。CSV は `サポートチーム代理店管理 - 光回線代理店情報.csv` または `seed_context.py` 内のファイル名に合わせて配置。
- GEMINI_API_KEY 未設定時は「Manual check required」等のフォールバックで動作。

---

## 8. Ver 更新時のルール（差分チェック・未反映の反映）

- **読み込みの保持:** 既存の実装（例: 知能データベースの件数・一覧）はメモリに残す。Ver 更新のたびに「簡易版（4件だけ）」などに戻さない。
- **差分チェック:** axiom_server.py / portal/src/App.jsx 等を Ver アップする際は、**変更前と変更後の差分**を確認する。特に以下をチェックする。
  - **portal/src/App.jsx の REAL_KNOWLEDGE:** CS 知能データベースは **12件**（seed_cs_knowledge.py の operation_sheets + talk_scripts + system_security と一致）。拡張時は **14件**（finance・NUROキャンペーン等を含む）とする。Ver 更新で 4 件に減っていないか確認し、減っていれば 12/14 件に復元する。
  - **portal/src/App.jsx の renderTextWithLinks（URL自動リンク化）:** §12 の不動ルール。AI メッセージ表示で URL を青いクリック可能リンクに変換するこの関数が削除されていないか確認し、削除されていれば復元する。
  - **axiom_server.py:** `/api/ingest` の有無、load_cache の clear+extend、save_cache の try/except、bi_endpoint の execution_status 互換など、既存挙動が落ちていないか確認する。
- **未反映の反映:** 差分で「以前あったが新 Ver で消えた」項目（上記 REAL_KNOWLEDGE、renderTextWithLinks、ingest ルート等）は、**未反映として検出し、必ず反映させる**。

---

## 11. Gemini UX 実装仕様（Ver 3.6.2）

ポータル（portal/src/App.jsx）を Google Gemini 本体のダークモードに極めて近い UX に刷新した際の仕様です。

- **配色**
  - メイン背景: `#131314`
  - サイドバー: `#1e1f20`
  - テキスト: `#e3e3e3`（本文）、`#8e918f`（補助）
  - 入力エリア: ホバーで `border-[#3c4043]`、フォーカスで `bg-[#28292a]`
- **レイアウト**
  - 左サイドバーに「組織知能データベース」12件＋「最近のプロトコル」を集約。Gemini の「最近の履歴」「拡張機能」風。
  - メインはチャット画面。ユーザーは右バブル、AI は左に Zap アイコン＋オープン表示（吹き出しなし）。
  - 画面下部にフローティング・インプット（丸みを帯びた大きな入力ボックス）。入力中は影・フォーカス強調。
- **ナビゲーション**
  - サイドバー下部: Chat / Dashboard / Token。ヘッダーでサイドバー開閉（Chevron）。
- **サーバー同期**
  - axiom_server.py Ver 3.6.2 で起動メッセージを「GEMINI EDITION SYNC」、BI の tier を「Enterprise V3.6.2 (Gemini-UX Sync)」に統一。キャッシュ表示名は `axiom_v362_gemini_cache`。
  - システムプロンプトに「Axiom の実行コア（Gemini Edition）」および Slack/kintone の execute_command 例を明記。

---

## 12. ポータル表示の不動ルール（Ver 3.6.8 — URL リンク化）

以下は **今後の Ver 更新で削除・無効化してはならない** ポータル仕様です。

- **renderTextWithLinks（URL 自動リンク化）**
  - **目的:** AI の返答テキストに含まれる URL を、青（`#1d9bf0`）のクリック可能なリンクに変換し、別タブで開く。
  - **実装:** `portal/src/App.jsx` 内で `renderTextWithLinks(input)` を定義し、メッセージ表示部分（`m.text` の描画）でこの関数の戻り値を表示する。
  - **仕様:**
    - `https?://` で始まる文字列を正規表現で検出し、`<a href={cleanUrl} target="_blank" rel="noopener noreferrer">` でラップする。
    - URL の末尾に「。」「」」「』」」「、」が付いている場合は、**リンクの href と表示テキストからそれらを除く**（リンクが壊れないようにする）。除去した記号はリンクの直後に通常テキストとして表示する。
  - **差分チェック:** §8 に従い、Ver 更新時に `renderTextWithLinks` が消えていないか確認し、消えていれば必ず復元する。

- **REAL_KNOWLEDGE:** 14 件（§8 の拡張時）を維持。Intel Highlights のグリッドで表示。

---

## 13. 答えファースト・プロトコル（Ver 3.7.1 — 不動のルール）

以下は **今後の Ver 更新で削除・無効化してはならない** サーバー側の回答品質ルールです。

- **思考プロセス（CoT）の非表示**
  - AI は頭の中で「1. 意図特定、2. 資料スキャン、3. 回答生成」を行うが、**action_instruction（回答本文）には結論・答えのみ**を書く。内部プロセスや「スキャンしました」「意図を特定しました」等の自己紹介は書かない。
- **メタ発言の禁止**
  - 「スキャンした結果、〜がありました」「〜に基づき回答します」といった説明臭い前置きは禁止。専門家が即答する「答えファースト」の構成とする。
- **聞き返しの最終手段化**
  - 資料に答えが 1% でも含まれていれば推測を含めて回答する。完全にゼロの場合のみ「どの資料を追加すべきか」を人間（佐藤様）に問う。
- **ノイズ・サプレッサー（deep_clean_text）**
  - AI が思考プロセスを回答文に書いてしまった場合、サーバー側で「したがって、」「回答します。」「答えは」以降のみを抽出して返す。

---

## 14. URL 整合性維持（Ver 3.7.4 — 不動のルール）

以下は **今後の Ver 更新で削除・無効化してはならない** URL まわりの仕様です。

- **サーバー（axiom_server.py）**
  - **deep_clean_text:** URL の末尾に付いている `)` `。」` `]` `』` などの記号を強制的に切り離し、スペースで「隔離」する。AI が `(URL:https://.../)` と出力しても、`( URL: https://.../ )` のように自動修正してから返す。リンク壊れを防ぐ。
- **ポータル（App.jsx）**
  - **renderTextWithLinks:** リンク化の正規表現を厳密にし、URL の直後にある記号（`)` `）` `]` `」` `』` `。` `、` `,` 等）を**リンク範囲から除外**する。除外した記号はリンクの直後に通常テキストとして表示する。
- **差分チェック:** §8 に従い、Ver 更新時に上記 URL 隔離・リンク範囲除外が消えていないか確認する。

---

## 15. クオリティ・センチネル・プロトコル（Ver 3.8.3 — 不動のルール）

以下は **今後の Ver 更新で削除・無効化してはならない** 組織知能の優先順位ルールです。

- **ナレッジ参照の絶対優先順位**
  1. **最優先:** 佐藤直が追加した `on_demand_docs`。ここに書かれた内容は最新の正解であり、他の全ての資料（固定マニュアル含む）を上書きする。
  2. 現場の成功ログ: `EXTRACTED_PROTOCOLS`。
  3. 公的な基本資料: 15個の固定ナレッジ、Google Drive。

- **出典レイヤー（タグ）の義務化**
  - AI の回答本文の冒頭に、どのレイヤーを参照したかタグを付与する。例: `[最新/依頼]` `[基本資料]` `[登録完了]`。

- **検証**
  - `qa_quality_benchmark.py` で、マニュアルは「即キャンセル」・on_demand_docs は「保留」としたとき、AI が「保留」と答えるかを検証する。

---

## 16. ホットフィックス・自信スコア・永続化＆スレッド（Ver 3.8.4 — 3.8.6）

### Ver 3.8.4 — ホットフィックス・インテリジェンス

- **ホットフィックス・プロトコル:** ユーザーが「その回答は間違い」「正解は○○だ」と修正指示した場合、即座に `execute_command` で `ingest_knowledge` を発行し、on_demand_docs に上書き登録する。
- **完了タグ:** 回答冒頭に `[ホットフィックス完了]`（修正時）または `[登録完了]`（通常登録時）を付与。`hotfix_intelligence_test.py` で検証。

### Ver 3.8.5 — 自信スコア（Confidence Mapping）

- **自信スコア（confidence_score）:** AI が 1–100 の自信度を返し、`autonomous_action.confidence` として API に含める。UI で CONFIDENCE 表示（90+ 緑、70+ 青、未満は橙）。
- **最短品質向上:** 自信が 70 未満の場合は `inquiry_to_human` で「自信がありません。正しい資料はこれですか？」と確認する指示をシステムプロンプトに追加。
- **tier:** `Enterprise V3.8.5 (Confidence)`。キャッシュ名: `axiom_v385_confidence_cache`。

### Ver 3.8.6 — 永続化・スレッド・マルチモーダル（Persistence & Threading）

- **Firebase 完全永続化:** フロント（ポータル）で Firestore にメッセージを保存。画面更新しても会話・スレッドが消えない。
- **インライン・スレッド:** メッセージのアイコンでその投稿に紐づく会話をインライン展開。`parentId` で親子関係を管理。
- **マルチモーダル添付:** 画像・ファイルをメッセージに添付可能。サーバーは `POST /api/logs` の `attachments`（base64 + mime_type）を受け取り、Gemini に Part（テキスト + `Part.from_bytes` 画像）として渡し、視覚情報を考慮した回答を生成する。
- **スレッド文脈の API 対応:** `parentId`・`thread_messages`（または `threadContext`）をペイロードで受け取り、プロンプトに「【スレッド文脈】」として直近10件を付与。AI がスレッドの流れを踏まえて回答。
- **メタ情報:** 返却の `meta` に `parentId`・`attachments_count` を追加。tier: `Enterprise V3.8.6 (Persistence & Threading)`。キャッシュ名: `axiom_v386_persistence_cache`。
- **自信スコアの継承:** Ver 3.8.5 の confidence 表示を統合 UI として維持。

---

*記録日: 2026年2月*
