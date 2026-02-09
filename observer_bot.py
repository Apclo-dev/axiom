"""
APCLO Eye - 現場観測エージェント
観測データを Central Brain (CENTRAL_BRAIN_URL) に送信する。
"""
import os
import json
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

CENTRAL_BRAIN_URL = os.getenv("CENTRAL_BRAIN_URL", "http://localhost:5000/api/logs")
CHATWORK_TOKEN = os.getenv("CHATWORK_TOKEN", "")


def send_log(payload: dict) -> bool:
    """観測ログを Central Brain に送信する。"""
    try:
        r = requests.post(
            CENTRAL_BRAIN_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[APCLO Eye] 送信エラー: {e}")
        return False


def observe_and_send(source: str, data: dict) -> bool:
    """観測結果をタイムスタンプ付きで送信。"""
    payload = {
        "source": "apclo_eye",
        "observer": source,
        "timestamp": datetime.now().isoformat(),
        "data": data,
    }
    return send_log(payload)


if __name__ == "__main__":
    print("APCLO Eye - 現場観測エージェント")
    print(f"Central Brain: {CENTRAL_BRAIN_URL}")
    # テスト送信
    ok = observe_and_send("test", {"message": "Hello from APCLO Eye"})
    print("送信結果:", "OK" if ok else "NG")
