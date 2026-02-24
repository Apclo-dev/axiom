# Axiom OS — Lead Me（実装サマリ）

このドキュメントは、**ここまでの実装内容**を要約し、プロジェクトの導き（Lead Me）として参照できるようにしたものです。

---

## 現在のバージョン

**Axiom OS Ver 3.8.6 — Persistence & Threading**

- **バックエンド:** `axiom_server.py`（Flask + Gemini 2.0 Flash）
- **ポート:** 5001
- **tier:** Enterprise V3.8.6 (Persistence & Threading)

---

## ここまでの実装の核心（Ver 3.8.4 ～ 3.8.6）

| 項目 | 内容 |
|------|------|
| **Firebase による完全永続化** | 画面を更新しても会話やスレッドが消えないよう、フロントで Firestore にメッセージを保存。 |
| **インライン・スレッド** | メッセージのアイコンでその投稿に紐づいた会話をインライン展開し、文脈を維持したやり取りを可能に。 |
| **マルチモーダル添付** | 画像やファイルをメッセージに添付可能。サーバーは `attachments` を受け取り、Gemini に画像 Part として渡し、視覚情報を考慮した回答を生成。 |
| **自信スコアの継承** | 前バージョンで実装した自信スコア（Confidence）を API・UI で維持。70 未満の場合は inquiry で確認を促す。 |
| **ホットフィックス** | 「その回答は間違い」「正解は○○だ」の指示で即座に ingest_knowledge を発行し、on_demand_docs に上書き。 |

---

## 主要 API（axiom_server.py）

| エンドポイント | 説明 |
|----------------|------|
| `POST /api/logs` | ログ受信。`body` / `user` / `platform` に加え、Ver 3.8.6 で `parentId`・`thread_messages`・`attachments` をオプションで受け付け。 |
| `POST /api/ingest` | 組織コンテキスト・on_demand_docs・Google Drive Index の投入。 |
| `GET /api/axiom-bi` | BI 用サマリ（total_logs, execution_count, knowledge_gaps, on_demand_docs, tier 等）と bi_ready_logs。 |

---

## 起動方法

```bash
./venv/bin/python axiom_server.py
```

起動メッセージ: `Axiom OS Ver 3.8.6: PERSISTENCE & THREADING (Port 5001)`

---

## 関連ドキュメント

- 詳細な実装記録・不動ルール: [IMPLEMENTATION.md](./IMPLEMENTATION.md)
- クイックスタート・環境変数: [README.md](./README.md)
- トラブルシューティング: [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

*更新: 2026年2月*
