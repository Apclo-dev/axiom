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
  - `CENTRAL_BRAIN_URL` … 脳のエンドポイント（デフォルト: http://localhost:5000/api/logs）
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
- `http://localhost:5000/api/axiom-bi` を 10 秒ごと + 強制更新ボタンで取得。
- 表示: Total Logs Processed、Axiom 2: Protocols Extracted、Average Urgency（bi_ready_logs から算出）、Recent Decisions（カード）、Extracted Logic（プロトコル一覧）。
- 接続失敗時はエラーメッセージ表示。XSS 対策のため `escapeHtml()` でエスケープ。

---

## 6. テスト・検証

- **learning_loop_test.py:** エキスパートの知恵が組織ルールとして AI に継承されるか（Axiom 2 & 5）を検証。田中氏の「Google Map で確認」ルール → 新人の質問に対する回答に「Google Map」が含まれるかで成功/失敗を判定。
- **sonet_auto_worker_v2_1.py:** 自律タスク完了を脳に報告する流れのシミュレーション。

---

## 7. 運用メモ

- 脳の起動: `./venv/bin/python mock_backend.py`（ポート 5000）
- コマンドセンター: ブラウザで `index.html` を開く（file:// または同一オリジンの HTTP）。CORS は mock_backend で許可済み。
- 代理店コンテキスト投入: 脳起動後に `./venv/bin/python seed_context.py`。CSV は `サポートチーム代理店管理 - 光回線代理店情報.csv` または `seed_context.py` 内のファイル名に合わせて配置。
- GEMINI_API_KEY 未設定時は「Manual check required」等のフォールバックで動作。

---

*記録日: 2026年2月*
