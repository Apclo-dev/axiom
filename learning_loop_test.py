import requests
import time

# Axiom OS Core Endpoint
BASE_URL = "http://localhost:5000/api/logs"

def run_feedback_loop_verification():
    """
    エキスパートの知恵が「組織のルール」としてAIに継承されるか（Axiom 2 & 5）を検証。
    """
    print("🧪 [Axiom Test v2.1] 自律進化（学習ループ）の検証開始\n")

    # 1. エキスパート（田中氏）が新しいロジック（暗黙知）を現場で発言したと仮定
    print("Step 1: エキスパート（田中氏）による新しい判断基準の提示...")
    logic_input = {
        "user": "田中",
        "platform": "Chatwork",
        "body": (
            "不備対応の新しいプロトコルです。住所不一致の案件については、即キャンセルせず、"
            "必ず Google Map で建物名まで確認してください。確認できたらURLを添えて"
            "管理画面へ差し戻す。これを組織の標準フローとします。"
        )
    }
    try:
        res1 = requests.post(BASE_URL, json=logic_input)
        if res1.status_code == 200:
            print(f"  -> Axiom分析（抽出）: {res1.json()['decision']['autonomous_action']['instruction']}")
        else:
            print(f"  ❌ Step 1 失敗: {res1.status_code}")
            return
    except Exception as e:
        print(f"  ❌ Step 1 エラー: {e}")
        return

    print("\n--- AIが知恵を消化中（3秒待機） ---\n")
    time.sleep(3)

    # 2. 別のユーザー（新人）が、同じような状況に遭遇して質問を投げる
    print("Step 2: 別のユーザー（新人）からの報告（学習効果の確認）...")
    query_input = {
        "user": "新人A",
        "platform": "GoogleChat",
        "body": "住所が間違っている可能性がある案件を見つけました。すぐにキャンセルして良いですか？"
    }
    try:
        res2 = requests.post(BASE_URL, json=query_input)
        if res2.status_code == 200:
            decision = res2.json()['decision']
            print(f"  🔍 AIの回答: {decision['autonomous_action']['instruction']}")
            print(f"  🧠 判断根拠: {decision['autonomous_action']['reasoning']}")

            # 田中氏が提示した「Google Map」というキーワードが回答に含まれているかチェック
            if "Google Map" in decision['autonomous_action']['instruction']:
                print("\n✅ 検証成功: AIはエキスパートの知恵を学習し、組織全体の回答として反映しました。")
            else:
                print("\n⚠️ 検証失敗: ロジックが継承されていません。")
        else:
            print(f"  ❌ Step 2 失敗: {res2.status_code}")
    except Exception as e:
        print(f"  ❌ Step 2 エラー: {e}")

if __name__ == "__main__":
    run_feedback_loop_verification()
