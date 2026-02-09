from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# CORSを有効化し、index.htmlからのアクセスを許可
CORS(app)

# --- 永続化ストレージ ---
axiom_intelligence_storage = []
# 抽出されたプロトコル（Axiom 2によって動的に蓄積）
EXTRACTED_PROTOCOLS = []

# --- 組織コンテキスト (Axiom Brain Knowledge Base) ---
# 初期値は最小限に留め、ingest APIやAIの抽出によって動的に拡張される設計
ORGANIZATIONAL_CONTEXT = {
    "agencies": {},    # 代理店マスターデータ
    "workflows": {},   # 業務フロー定義
    "rules": {},       # 運用ルール・公理適用基準
    "experts": [],     # 意思決定権限者・エキスパートリスト
    "metadata": {}     # その他、限定しない任意のコンテキスト
}

# Gemini API 設定
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')


class AxiomOSCore:
    """
    組織の全コンテキストを保持し、5つの公理に基づいて判断を出力するコア・エンジン
    """
    def __init__(self):
        self.axioms = {
            1: "Data Integrity",
            2: "Algorithmization",
            3: "Execution Value",
            4: "Lead Time Cost",
            5: "Autonomous Evolution"
        }

    def ingest_context(self, category, data):
        """
        組織情報をAxiomに読み込ませる。
        既存のカテゴリにマージ、または新しいカテゴリを動的に作成する。
        """
        if category not in ORGANIZATIONAL_CONTEXT:
            ORGANIZATIONAL_CONTEXT[category] = {}

        if isinstance(data, dict):
            ORGANIZATIONAL_CONTEXT[category].update(data)
        elif isinstance(data, list):
            if not isinstance(ORGANIZATIONAL_CONTEXT[category], list):
                ORGANIZATIONAL_CONTEXT[category] = []
            ORGANIZATIONAL_CONTEXT[category].extend(data)
            # 重複削除（文字列リストの場合）
            if all(isinstance(x, str) for x in ORGANIZATIONAL_CONTEXT[category]):
                ORGANIZATIONAL_CONTEXT[category] = list(set(ORGANIZATIONAL_CONTEXT[category]))
        else:
            ORGANIZATIONAL_CONTEXT[category] = data

        print(f"✅ [Axiom Brain] Context Updated: '{category}'")

    async def analyze_with_gemini(self, content, user, platform):
        """
        過去のプロトコルと、動的に拡張された全コンテキストをGeminiにインジェクションする
        """
        protocol_context = json.dumps(EXTRACTED_PROTOCOLS[-15:], ensure_ascii=False)
        full_context = json.dumps(ORGANIZATIONAL_CONTEXT, ensure_ascii=False)

        system_prompt = f"""
        あなたは組織の自律OS「Axiom OS」の核となる知能です。
        以下の「5つの公理」と、動的に更新される「組織コンテキスト」を完全に理解し、現場ログを解析してください。

        【5つの公理】
        1. データ整合性 2. 属人化解体 3. 実行価値 4. リードタイム 5. 自律進化

        【組織コンテキスト (最新)】
        {full_context}

        【学習済みプロトコル (Axiom 2)】
        {protocol_context}

        【出力形式 (JSON)】
        {{
            "aligned_axiom": [番号],
            "urgency_score": 1-10,
            "logic_extraction": "抽出された判断基準や手順（Axiom 2用）",
            "action_instruction": "具体的な実行命令",
            "reasoning": "どのコンテキストに基づき判断したか"
        }}
        """
        user_prompt = f"Platform: {platform}\nUser: {user}\nContent: {content}"

        try:
            response = model.generate_content(
                f"{system_prompt}\n\n{user_prompt}",
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"❌ Gemini Error: {e}")
            return None

    async def process_input(self, input_payload):
        body = input_payload.get('body') or input_payload.get('text') or ''
        user = input_payload.get('user') or 'Unknown'
        platform = input_payload.get('platform') or 'Unknown'

        analysis = await self.analyze_with_gemini(body, user, platform)

        if not analysis:
            analysis = {
                "aligned_axiom": [0],
                "urgency_score": 1,
                "logic_extraction": "N/A",
                "action_instruction": "Manual check required",
                "reasoning": "API Error"
            }

        # Axiom 2 の場合、動的にプロトコルを蓄積
        if 2 in analysis.get('aligned_axiom', []) and analysis.get('logic_extraction') != "N/A":
            EXTRACTED_PROTOCOLS.append({
                "timestamp": datetime.now().isoformat(),
                "user": user,
                "logic": analysis['logic_extraction']
            })

        decision = {
            "id": len(axiom_intelligence_storage) + 1,
            "timestamp": datetime.now().isoformat(),
            "axiom_impact": {
                "primary_axiom": analysis.get('aligned_axiom', [0]),
                "urgency": analysis.get('urgency_score', 1)
            },
            "autonomous_action": {
                "instruction": analysis.get('action_instruction', ''),
                "reasoning": analysis.get('reasoning', '')
            },
            "meta": {"user": user, "platform": platform, "body": body}
        }
        return decision


axiom_brain = AxiomOSCore()

# --- API Endpoints ---


@app.route('/api/ingest', methods=['POST'])
def ingest_data():
    """コンテキストの注入（既存カテゴリの上書き・マージ、新規追加）"""
    data = request.json
    category = data.get('category', 'metadata')
    payload = data.get('payload', {})
    axiom_brain.ingest_context(category, payload)
    return jsonify({"status": "Context Synced", "current_categories": list(ORGANIZATIONAL_CONTEXT.keys())}), 200


@app.route('/api/stores/upsert', methods=['POST'])
def upsert_stores():
    """外部連携用エイリアス"""
    data = request.json
    axiom_brain.ingest_context('agencies', data)
    return jsonify({"status": "Success"}), 200


@app.route('/api/logs', methods=['POST'])
async def handle_input():
    raw_input = request.json
    output = await axiom_brain.process_input(raw_input)
    axiom_intelligence_storage.append(output)
    print(f"\n🧠 [Axiom Decision] >>> {output['autonomous_action']['instruction']}")
    return jsonify({"status": "Processed", "decision": output}), 200


@app.route('/api/axiom-bi', methods=['GET'])
def get_bi_data():
    flat_logs = []
    for log in axiom_intelligence_storage:
        primary = log["axiom_impact"].get("primary_axiom")
        flat_logs.append({
            "id": log["id"],
            "timestamp": log["timestamp"],
            "user": log["meta"]["user"],
            "platform": log["meta"]["platform"],
            "message": log["meta"]["body"],
            "primary_axiom": primary[0] if primary else 0,
            "urgency": log["axiom_impact"].get("urgency", 1),
            "instruction": log["autonomous_action"]["instruction"],
            "reasoning": log["autonomous_action"]["reasoning"]
        })
    return jsonify({
        "summary_stats": {
            "total_logs": len(axiom_intelligence_storage),
            "logic_extractions": len(EXTRACTED_PROTOCOLS),
            "context_categories": list(ORGANIZATIONAL_CONTEXT.keys())
        },
        "bi_ready_logs": flat_logs,
        "new_protocols": EXTRACTED_PROTOCOLS,
        "raw_context_snapshot": ORGANIZATIONAL_CONTEXT
    }), 200


if __name__ == '__main__':
    print("🚀 Axiom OS AI-Engine (Flexible Context) is running on http://localhost:5000")
    app.run(port=5000, debug=True)
