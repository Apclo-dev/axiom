# Axiom OS

組織の「脳」として現場ログを収集・解析し、5つの公理に基づいて自律判断を出力するシステムです。

## 5つの公理

1. **Data Integrity**（データ整合性）  
2. **Algorithmization**（属人化解体）  
3. **Execution Value**（実行価値）  
4. **Lead Time Cost**（速度追求）  
5. **Autonomous Evolution**（自律進化）

## クイックスタート

```bash
# 仮想環境と依存関係
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 環境変数（.env に GEMINI_API_KEY 等を設定）
cp .env.example .env   # 必要に応じて編集

# 脳（Axiom OS Core）の起動
./venv/bin/python mock_backend.py
```

ブラウザで `index.html` を開くとコマンドセンターからリアルタイムで判断ログを確認できます。

## 主なファイル

| ファイル | 説明 |
|----------|------|
| `mock_backend.py` | Axiom OS コア（Flask + Gemini）。`/api/logs`, `/api/ingest`, `/api/axiom-bi` を提供。 |
| `index.html` | コマンドセンター（BI ダッシュボード）。 |
| `seed_context.py` | 代理店 CSV を脳に投入。 |
| `observer_bot.py` | APCLO Eye（現場観測エージェント）。 |
| `sonet_auto_worker_v2_1.py` | 自律実行ワーカーのシミュレーション。 |
| `learning_loop_test.py` | エキスパートの知恵が AI に継承されるか検証。 |

## 環境変数（.env）

- `GEMINI_API_KEY` … Gemini API キー（未設定時はフォールバック）
- `CENTRAL_BRAIN_URL` … 脳のエンドポイント（デフォルト: http://localhost:5000/api/logs）
- `CHATWORK_TOKEN` … Chatwork 連携（任意）
- `GCHAT_SPACE_A_URL` / `GCHAT_SPACE_B_URL` … Google Chat（任意）

## 実装の詳細

詳細な実装記録は [IMPLEMENTATION.md](./IMPLEMENTATION.md) を参照してください。

## ライセンス

Private / 社内利用を想定しています。
