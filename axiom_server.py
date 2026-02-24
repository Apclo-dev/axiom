import base64
import json
import os
import atexit
import asyncio
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from dotenv import load_dotenv

try:
    from action_dispatcher import ActionDispatcher
    dispatcher = ActionDispatcher()
except Exception as e:
    dispatcher = None
    print(f"⚠️ [Warning] ActionDispatcher failed to load: {e}")

load_dotenv(verbose=True)

app = Flask(__name__)
CORS(app)

PORT = 5001
CACHE_FILE = "axiom_context_v2_3.json"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
API_ACCESS_TOKEN = os.getenv("AXIOM_TOKEN", "axiom-secure-2026")
MODEL_ID = "gemini-2.0-flash"

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"🚀 Axiom OS Ver 3.8.6: PERSISTENCE & THREADING (Port {PORT})")
    except Exception as e:
        client = None
        print(f"❌ API Client Init Error: {e}")
else:
    client = None
    print("⚠️ WARNING: GEMINI_API_KEY not found in .env")

# --- 知能状態管理 (Ver 3.8.0: DRIVE_INDEX / on_demand_docs) ---
ORGANIZATIONAL_CONTEXT = {"agencies": {}, "workflows": {}, "rules": {}, "experts": [], "metadata": {}, "on_demand_docs": []}
axiom_intelligence_storage = []
EXTRACTED_PROTOCOLS = []
KNOWLEDGE_GAPS = []  # AIが答えられなかった「欠損知識」のリスト
DRIVE_INDEX = []  # Google Drive 連携で取得したファイル一覧
cached_content_name = None
cache_expire_time = None
execution_counter = 0


def save_cache():
    data = {
        "context": ORGANIZATIONAL_CONTEXT,
        "logs": axiom_intelligence_storage,
        "protocols": EXTRACTED_PROTOCOLS,
        "gaps": KNOWLEDGE_GAPS,
        "drive_index": DRIVE_INDEX,
        "exec_count": execution_counter,
        "tier": "Enterprise/Ver3.8.6"
    }
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 [Brain] State secured (On-Demand: {len(ORGANIZATIONAL_CONTEXT.get('on_demand_docs', []))})")
    except Exception as e:
        print(f"⚠️ Cache Save Error: {e}")


def load_cache():
    global axiom_intelligence_storage, EXTRACTED_PROTOCOLS, KNOWLEDGE_GAPS, DRIVE_INDEX, execution_counter
    if not os.path.exists(CACHE_FILE):
        return
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if "context" in data:
            ORGANIZATIONAL_CONTEXT.update(data["context"])
        if "logs" in data:
            axiom_intelligence_storage.clear()
            axiom_intelligence_storage.extend(data["logs"])
        if "protocols" in data:
            EXTRACTED_PROTOCOLS.clear()
            EXTRACTED_PROTOCOLS.extend(data["protocols"])
        if "gaps" in data:
            KNOWLEDGE_GAPS.clear()
            KNOWLEDGE_GAPS.extend(data["gaps"])
        if "drive_index" in data:
            DRIVE_INDEX.clear()
            DRIVE_INDEX.extend(data["drive_index"])
        execution_counter = data.get("exec_count", 0)
        print(f"📂 Intelligence Restored: {len(axiom_intelligence_storage)} logs, {len(ORGANIZATIONAL_CONTEXT.get('on_demand_docs', []))} on-demand docs.")
    except Exception as e:
        print(f"⚠️ Cache Load Error: {e}")


atexit.register(save_cache)


def is_authorized(req):
    auth_header = req.headers.get('Authorization')
    if auth_header == f"Bearer {API_ACCESS_TOKEN}":
        return True
    if req.remote_addr in ["127.0.0.1", "localhost"]:
        return True
    return False


class AxiomOSCore:
    def deep_clean_text(self, text):
        """URL隔離・ノイズ剥ぎ取り・出典タグの整形（Ver 3.8.6）"""
        if not text:
            return ""
        text = str(text).strip()
        text = re.sub(r'```json\s*|\s*```', '', text)
        text = re.sub(r'\\+', ' ', text)
        url_pattern = r'(https?://\S+)'
        def url_isolate(match):
            url = match.group(1)
            clean_url = re.sub(r'[)）\]」』》。、,]+$', '', url)
            trailing = url[len(clean_url):]
            return f" {clean_url} {trailing} " if trailing else f" {clean_url} "
        text = re.sub(url_pattern, url_isolate, text)
        return re.sub(r'\s{2,}', ' ', text).strip()

    async def get_or_create_cache(self, system_instruction):
        global cached_content_name, cache_expire_time
        if cached_content_name and cache_expire_time and datetime.now() < cache_expire_time:
            return cached_content_name
        if not client:
            return None
        try:
            cache = client.caches.create(
                model=MODEL_ID,
                config=types.CreateCachedContentConfig(
                    display_name="axiom_v386_persistence_cache",
                    system_instruction=system_instruction,
                    ttl="3600s"
                )
            )
            cached_content_name = cache.name
            cache_expire_time = datetime.now() + timedelta(hours=1)
            print(f"✅ [Cache] Synchronized: {cached_content_name}")
            return cached_content_name
        except Exception as e:
            return None

    def _build_content_parts(self, user_input_text, attachments):
        """Ver 3.8.6: テキスト + 添付（画像等）を Gemini Part のリストに変換。"""
        parts = [types.Part.from_text(text=user_input_text)]
        if not attachments:
            return parts
        for att in attachments[:10]:  # 最大10件
            raw = att.get("data") or att.get("content") or ""
            if not raw:
                continue
            if isinstance(raw, str) and raw.startswith("data:"):
                raw = raw.split(",", 1)[-1]
            try:
                data = base64.b64decode(raw) if isinstance(raw, str) else raw
            except Exception:
                continue
            mime = (att.get("type") or att.get("mime_type") or "image/png").split(";")[0].strip()
            if not mime.startswith("image/"):
                mime = "application/octet-stream"
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))
        return parts

    async def process_input(self, payload):
        global execution_counter
        body = payload.get('body') or payload.get('text') or ''
        user = payload.get('user') or 'Unknown'
        platform = payload.get('platform') or 'Unknown'
        parent_id = payload.get('parentId') or payload.get('parent_id')
        thread_messages = payload.get('thread_messages') or payload.get('threadContext') or []
        attachments = payload.get('attachments') or []

        full_ctx = json.dumps(ORGANIZATIONAL_CONTEXT, ensure_ascii=False)[:30000]
        recent_p = json.dumps(EXTRACTED_PROTOCOLS[-15:], ensure_ascii=False)
        drive_ctx = json.dumps(DRIVE_INDEX, ensure_ascii=False)

        # --- Ver 3.8.6: スレッド文脈を冒頭に付与（AIが文脈を考慮して回答）---
        thread_section = ""
        if thread_messages:
            lines = ["【スレッド文脈】"]
            for m in thread_messages[-10:]:
                role = m.get("role") or m.get("sender", "user")
                text = (m.get("text") or m.get("body") or "").strip()
                if text:
                    lines.append(f"{role}: {text[:500]}")
            thread_section = "\n".join(lines) + "\n\n"

        # --- Ver 3.8.5 継承: 自信スコア + 最短品質向上 ---
        on_demand_json = json.dumps(ORGANIZATIONAL_CONTEXT.get('on_demand_docs', []), ensure_ascii=False)
        system_instruction = f"""
        あなたは組織OS「Axiom」の品質監視型知能です。

        【行動指針：最短品質向上】
        1. ユーザー（特に佐藤直）が「その回答は間違い」「正解は○○だ」と言った場合、自らの非を認め、即座に ingest_knowledge コマンドで情報を上書きせよ。
        2. 回答の冒頭には必ず [出典レイヤー] を付け、自信の度合い(1-100)を confidence_score で返せ。
        3. 自信が 70 未満の場合は、inquiry_to_human で「自信がありません。正しい資料はこれですか？」と確認せよ。
        4. スレッド文脈や添付画像・ファイルが渡された場合は、それらを踏まえて回答せよ（マルチモーダル）。

        【ナレッジ優先度】on_demand_docs 最優先 → EXTRACTED_PROTOCOLS → 固定資料/Drive。

        【組織知能：on_demand_docs】{on_demand_json}
        【組織情報】{full_ctx}
        【Google Drive Index】{drive_ctx}
        【最新プロトコル】{recent_p}
        """
        user_input = f"{thread_section}User: {user} ({platform})\n【今回の入力】\n{body}"
        cache_name = await self.get_or_create_cache(system_instruction)

        try:
            content_parts = self._build_content_parts(user_input, attachments)
            config = types.GenerateContentConfig(cached_content=cache_name) if cache_name else None
            if cache_name and len(content_parts) == 1:
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=content_parts[0].text,
                    config=config
                )
            elif content_parts and client:
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=content_parts,
                    config=config
                )
            else:
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=[system_instruction, user_input]
                )
            raw_output = (response.text or "").strip()
            print(f"\n--- [DEBUG] AI Raw ---\n{raw_output[:300]}...")

            # Ver 3.8.1: JSON抽出ロジック強化（```json 優先 → { } ブロック）
            cleaned_json = None
            if "```json" in raw_output:
                m = re.search(r'```json\s*(.*?)\s*```', raw_output, re.DOTALL)
                if m:
                    cleaned_json = m.group(1).strip()
            if not cleaned_json:
                json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)
                if json_match:
                    cleaned_json = json_match.group(0)
            if cleaned_json:
                analysis = json.loads(cleaned_json)
            else:
                # Ver 3.8.3/3.8.4: JSON がなくても出典タグ付き本文 or 短いテキストなら採用
                t = raw_output.strip()
                if t and (t.startswith("[最新/依頼]") or t.startswith("[基本資料]") or t.startswith("[登録完了]") or t.startswith("[ホットフィックス完了]") or (len(t) < 2000 and "{" not in t[:100])):
                    analysis = {"action_instruction": t}
                else:
                    analysis = {"action_instruction": t if t else "解析エラー。簡潔な指示をお願いします。"}
        except Exception as e:
            print(f"❌ Analysis Error: {e}")
            analysis = {"action_instruction": "解析エラー。簡潔な指示をお願いします。"}

        # 最終クレンジング（str(analysis) は絶対に使わない）
        raw_instruction = analysis.get('action_instruction') or analysis.get('response')
        if raw_instruction is not None and not isinstance(raw_instruction, str):
            raw_instruction = None
        instruction = self.deep_clean_text(raw_instruction) if raw_instruction else ""
        # Ver 3.8.2/3.8.3: コマンド発行時に回答が空なら「登録完了報告」を自動生成
        if not instruction and analysis.get('execute_command'):
            cmd = analysis['execute_command']
            if cmd.get('command') == "ingest_knowledge":
                title = (cmd.get('params') or {}).get('title', '資料')
                instruction = f"[登録完了] 佐藤直様の指示に基づき、ナレッジ『{title}』を最優先データとして格納しました。"
        # 空 or 生JSONっぽい文字列なら人間らしいフォールバック
        if not instruction or "'action_instruction'" in instruction or '"action_instruction"' in instruction or "'reasoning'" in instruction:
            if any(x in (body or "") for x in ("ありがとう", "感謝", "thanks", "thank you", "助かった")):
                instruction = "どういたしまして！お役に立てて嬉しいです。"
            elif any(x in body for x in ("おはよう", "こんにちは", "こんばんは", "よろしく")):
                instruction = "こちらこそよろしくお願いします。何かあればお声がけください。"
            else:
                instruction = "承知しました。他にご用があればお知らせください。"
        inquiry = (analysis.get('inquiry_to_human') or "").strip() or None

        # 知能の欠損（Gap）を記録 — Dashboard の Knowledge Gaps に表示
        if inquiry and inquiry not in ["N/A", ""]:
            KNOWLEDGE_GAPS.append({
                "id": len(KNOWLEDGE_GAPS) + 1,
                "timestamp": datetime.now().isoformat(),
                "user_query": body,
                "ai_inquiry": inquiry,
                "status": "pending"
            })

        # 実行レイヤー
        exec_status = "None"
        if analysis.get('execute_command') and dispatcher:
            cmd = analysis['execute_command']
            res = dispatcher.dispatch(cmd)
            # Ver 3.8.5: Hot-Fix / Ingest 完了時の自動応答
            if cmd.get("command") == "ingest_knowledge":
                tag = "[ホットフィックス完了]" if ("間違い" in (body or "") or "正解は" in (body or "")) else "[登録完了]"
                instruction = f"{tag} 佐藤直様の指示に基づき、ナレッジ『{(cmd.get('params') or {}).get('title', '資料')}』を最優先データとして格納しました。"
            if res.get("status") == "success":
                exec_status = f"Success: {cmd.get('command')} dispatched."
                execution_counter += 1
            else:
                exec_status = f"Failed: {res.get('error', 'Unknown Error')}"

        # Axiom 2: 逆引きプロトコル（ユーザーが教えた知識を即座に保存）
        extracted = analysis.get('logic_extraction')
        if extracted and extracted not in ["N/A", "", None]:
            EXTRACTED_PROTOCOLS.append({
                "timestamp": datetime.now().isoformat(),
                "user": user,
                "logic": str(extracted)
            })

        return {
            "id": len(axiom_intelligence_storage) + 1,
            "timestamp": datetime.now().isoformat(),
            "axiom_impact": {
                "primary_axiom": analysis.get('aligned_axiom', [0]),
                "urgency": analysis.get('urgency_score', 1)
            },
            "autonomous_action": {
                "instruction": instruction,
                "confidence": analysis.get('confidence_score', 80),
                "reasoning": str(analysis.get('reasoning', 'Logic match')),
                "cited_sources": analysis.get('cited_sources', []),
                "inquiry": inquiry,
                "execution_status": exec_status
            },
            "meta": {"user": user, "platform": platform, "body": body, "parentId": parent_id, "attachments_count": len(attachments)}
        }


axiom_brain = AxiomOSCore()


@app.route('/api/ingest', methods=['POST'])
def handle_ingest():
    if not is_authorized(request):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    category = data.get('category', 'metadata')
    payload = data.get('payload', {})
    global DRIVE_INDEX, cached_content_name

    if category == "google_drive":
        DRIVE_INDEX.clear()
        DRIVE_INDEX.extend(payload if isinstance(payload, list) else [payload])
    else:
        if category not in ORGANIZATIONAL_CONTEXT:
            ORGANIZATIONAL_CONTEXT[category] = {}
        if isinstance(payload, dict):
            ORGANIZATIONAL_CONTEXT[category].update(payload)
        elif isinstance(payload, list):
            if not isinstance(ORGANIZATIONAL_CONTEXT[category], list):
                ORGANIZATIONAL_CONTEXT[category] = []
            ORGANIZATIONAL_CONTEXT[category].extend(payload)
        else:
            ORGANIZATIONAL_CONTEXT[category] = payload
    cached_content_name = None
    save_cache()
    print(f"✅ [Ingest] Context updated: {category}")
    return jsonify({"status": "Intelligence Synced", "category": category}), 200


@app.route('/api/logs', methods=['POST'])
def handle_logs():
    if not is_authorized(request):
        return jsonify({"error": "Unauthorized"}), 401
    output = asyncio.run(axiom_brain.process_input(request.json))
    axiom_intelligence_storage.append(output)
    save_cache()
    return jsonify({"status": "Processed", "decision": output}), 200


@app.route('/api/axiom-bi', methods=['GET'])
def handle_bi():
    if not is_authorized(request):
        return jsonify({"error": "Unauthorized"}), 401
    flat_logs = []
    for l in axiom_intelligence_storage[-50:]:
        act = dict(l.get("autonomous_action") or {})
        act.setdefault("execution_status", "None")
        flat_logs.append({
            "id": l["id"],
            "timestamp": l["timestamp"],
            "user": l["meta"]["user"],
            "platform": l["meta"].get("platform", ""),
            "message": l["meta"]["body"],
            "primary_axiom": l["axiom_impact"]["primary_axiom"][0] if l["axiom_impact"].get("primary_axiom") else 0,
            "instruction": act.get("instruction", ""),
            "autonomous_action": act
        })
    return jsonify({
        "summary_stats": {
            "total_logs": len(axiom_intelligence_storage),
            "logic_extractions": len(EXTRACTED_PROTOCOLS),
            "knowledge_gaps": len([g for g in KNOWLEDGE_GAPS if g.get("status") == "pending"]),
            "drive_files": len(DRIVE_INDEX),
            "on_demand_docs": len(ORGANIZATIONAL_CONTEXT.get("on_demand_docs", [])),
            "execution_count": execution_counter,
            "tier": "Enterprise V3.8.6 (Persistence & Threading)"
        },
        "bi_ready_logs": flat_logs,
        "knowledge_gaps": KNOWLEDGE_GAPS[-10:],
        "new_protocols": EXTRACTED_PROTOCOLS,
        "on_demand_list": ORGANIZATIONAL_CONTEXT.get("on_demand_docs", [])
    }), 200


if __name__ == '__main__':
    load_cache()
    app.run(host='0.0.0.0', port=PORT, debug=True)
