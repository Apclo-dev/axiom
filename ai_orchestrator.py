"""
AI Orchestrator - APCLO Eye オーケストレーター
観測エージェントと Central Brain の連携を管理する。
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

CENTRAL_BRAIN_URL = os.getenv("CENTRAL_BRAIN_URL", "http://localhost:5000/api/logs")
CHATWORK_TOKEN = os.getenv("CHATWORK_TOKEN", "")


def main():
    print("AI Orchestrator - 起動中...")
    print(f"Central Brain: {CENTRAL_BRAIN_URL}")
    if CHATWORK_TOKEN:
        print("Chatwork: トークン設定済み")
    else:
        print("Chatwork: 未設定 (CHATWORK_TOKEN)")
    # 観測エージェントをインポートしてテスト送信
    try:
        from observer_bot import observe_and_send
        ok = observe_and_send("orchestrator", {"event": "orchestrator_started"})
        print("Central Brain 疎通:", "OK" if ok else "NG")
    except Exception as e:
        print("observer_bot 連携:", e)
    print("オーケストレーター待機中 (Ctrl+C で終了)")
    try:
        while True:
            import time
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n終了しました。")


if __name__ == "__main__":
    main()
    sys.exit(0)
