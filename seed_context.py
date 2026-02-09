import pandas as pd
import requests
import os
import json

# Axiom OS のエンドポイント
INGEST_URL = "http://localhost:5000/api/ingest"

def seed_agency_data():
    """
    『光回線代理店情報.csv』を読み込み、Axiom OS のナレッジベースへ同期します。
    """
    # ファイル名は実際のパスに合わせて調整してください
    csv_file = "サポートチーム代理店管理 - 光回線代理店情報.csv"

    if not os.path.exists(csv_file):
        print(f"❌ Error: {csv_file} が見つかりません。プロジェクトルートに配置してください。")
        return

    try:
        # CSV読み込み (2行目の【入力必須】行をスキップ)
        df = pd.read_csv(csv_file, skiprows=[1])

        # 企業名をキーにした辞書構造へ変換
        agency_data = {}
        for _, row in df.iterrows():
            name = str(row.get('企業名', '')).strip()
            if name and name != 'nan':
                # NaN値をNone(JSONのnull)に変換してクリーンにする
                agency_data[name] = row.where(pd.notnull(row), None).to_dict()

        # Axiom OS へ送信
        payload = {
            "category": "agencies",
            "payload": agency_data
        }

        response = requests.post(INGEST_URL, json=payload)

        if response.status_code == 200:
            print(f"✅ 成功: {len(agency_data)} 社の代理店コンテキストを Axiom OS に同期しました。")
        else:
            print(f"❌ 失敗: ステータスコード {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ 実行エラー: {e}")

if __name__ == "__main__":
    seed_agency_data()
