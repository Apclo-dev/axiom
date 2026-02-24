import os
import requests
import json
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

class ActionDispatcher:
    """
    AIの判断を物理操作（Slack/kintone/Knowledge）へ変換する。
    Ver 3.8.0: オンデマンドなナレッジ注入（ingest_knowledge）を追加。
    """
    def __init__(self):
        self.axiom_api_base = os.getenv("AXIOM_API_BASE", "http://localhost:5001/api")
        self.axiom_token = os.getenv("AXIOM_TOKEN", "axiom-secure-2026")

        # kintone 設定
        self.kintone_domain = os.getenv("KINTONE_DOMAIN")
        self.kintone_token = os.getenv("KINTONE_TOKEN")
        self.kintone_app_id = os.getenv("KINTONE_APP_ID")

        # Slack 設定
        self.slack_token = os.getenv("SLACK_ACCESS_TOKEN")
        self.default_channel = os.getenv("SLACK_DEFAULT_CHANNEL")

        print(f"🔗 [Dispatcher] Slack Status: {'✅ READY' if self.slack_token else '❌ MISSING'}")
        print(f"🔗 [Dispatcher] kintone Status: {'✅ READY' if self.kintone_token else '❌ MISSING'}")

    def dispatch(self, command_data):
        """AIから生成されたコマンドを解析し、外部サービスへ実行"""
        if not command_data:
            return {"status": "skipped", "reason": "No command data"}

        cmd = command_data.get("command")
        params = command_data.get("params", {})

        print(f"⚡ [Dispatcher] Executing: {cmd}")

        try:
            # Ver 3.8.0: ナレッジの動的インジェクション
            if cmd == "ingest_knowledge":
                return self._ingest_to_axiom(params)
            if cmd == "slack_notify":
                return self._slack_api_post(params)
            if cmd == "kintone_update":
                return self._kintone_api_update(params)
            return {"status": "error", "error": f"Unknown command: {cmd}"}
        except Exception as e:
            print(f"❌ [Dispatcher Error] {e}")
            return {"status": "exception", "details": str(e)}

    def _ingest_to_axiom(self, params):
        """
        AIが抽出したURLと情報を Axiom のナレッジベースへ自律的に書き戻す
        """
        url = f"{self.axiom_api_base}/ingest"
        headers = {"Authorization": f"Bearer {self.axiom_token}", "Content-Type": "application/json"}
        doc = {
            "title": params.get("title", "新規依頼資料"),
            "url": params.get("url", ""),
            "ingested_at": params.get("ingested_at", "now"),
            "source": params.get("source", "Human Request via Chat")
        }
        payload = {"category": "on_demand_docs", "payload": [doc]}
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                print(f"🧠 [Self-Evolution] New Knowledge Integrated: {doc.get('title')}")
                return {"status": "success"}
            return {"status": "error", "error": res.text}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _slack_api_post(self, params):
        """Slack chat.postMessage API"""
        if not self.slack_token:
            return {"status": "error", "error": "Token missing"}
        url = "https://slack.com/api/chat.postMessage"
        headers = {"Authorization": f"Bearer {self.slack_token}", "Content-Type": "application/json"}
        channel = params.get("channel") or self.default_channel
        text = params.get("message", "Axiom Auto Report")

        payload = {
            "channel": channel,
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "🚀 Axiom 自律実行レポート", "emoji": True}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*指示内容:*\n{text}"}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": "📍 *Action by Axiom 3*"}]}
            ]
        }
        res = requests.post(url, headers=headers, json=payload, timeout=10).json()
        return {"status": "success"} if res.get("ok") else {"status": "error", "error": res.get("error")}

    def _kintone_api_update(self, params):
        """
        kintone レコード更新 API の実作。
        レコードのステータス変更と、AIの判断根拠の追記を自律的に行います。
        """
        if not all([self.kintone_domain, self.kintone_token, self.kintone_app_id]):
            print("⚠️ [kintone] 構成情報が不足しています。実効をスキップします。")
            return {"status": "error", "error": "Config missing"}

        record_id = params.get("record_id")
        if not record_id:
            return {"status": "error", "error": "No record_id provided"}

        url = f"https://{self.kintone_domain}/k/v1/record.json"
        headers = {
            "X-Cybozu-API-Token": self.kintone_token,
            "Content-Type": "application/json"
        }

        # 更新内容の構築（フィールドコードは現場のアプリ設定に合わせる）
        payload = {
            "app": self.kintone_app_id,
            "id": record_id,
            "record": {
                "ステータス": {"value": params.get("status", "不備確認中")},
                "AI判定理由": {"value": params.get("reason", "Axiom による自律更新")}
            }
        }

        try:
            res = requests.put(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                print(f"✅ [kintone] Record {record_id} successfully updated via API.")
                return {"status": "success", "target": "kintone"}
            else:
                try:
                    error_info = res.json().get("message", res.text)
                except Exception:
                    error_info = res.text
                print(f"❌ [kintone API Error] {error_info}")
                return {"status": "error", "error": error_info}
        except Exception as e:
            return {"status": "connection_error", "details": str(e)}


if __name__ == "__main__":
    # 単体接続テスト：このスクリプトを直接実行して確認可能
    d = ActionDispatcher()
    print("🧪 Dispatcher Ver 3.8.0 Standalone Test...")
    # d.dispatch({"command": "kintone_update", "params": {"record_id": "1", "status": "テスト中"}})
