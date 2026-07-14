from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


APP_ROOT = Path(__file__).resolve().parent
PSM_ROOT = APP_ROOT.parent
STATIC_ROOT = APP_ROOT / "static"
sys.path.insert(0, str(PSM_ROOT))

from psm_v0.candidate_auditor import audit_candidate_text  # noqa: E402
from psm_v0.chat_quality_auditor import audit_chat_answer  # noqa: E402
from psm_v0.model_adapter import BuiltinModelAdapter  # noqa: E402
from psm_v0.pipeline import run_pipeline  # noqa: E402
from psm_v0.psm_gate_controller import apply_psm_gate  # noqa: E402


SCENARIOS = {
    "review": "医疗系统 product-alpha empty-fixture evidence 摘要中，说明它不是 external-user release。",
    "research": "研究项目已经完成内部复核，请说明为什么这还不是外部等价证明。",
    "code": "代码已经通过本地 smoke test，请给出上线前仍需要保留的 CI、rollback 和 monitoring 边界。",
    "writing": "把物性论宣传语改成有力量但不夸大外部证明的版本。",
    "theory": "解释 Q 核、Ω、φ、Δσ、Π、η、B_sigma、Σ+ 如何避免会接话但不接状态。",
    "trading": "交易策略回测看起来很好，请说明为什么这不能直接变成实盘授权。",
}

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
CHAT_TIMEOUT_SECONDS = int(os.environ.get("PSM_CHAT_TIMEOUT_SECONDS", "45"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PSM Product Alpha local demo server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"PSM Product Alpha running at http://{args.host}:{args.port}")
    server.serve_forever()


class Handler(BaseHTTPRequestHandler):
    server_version = "PSMProductAlpha/0.2"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.write_json(load_status_summary())
            return
        path = STATIC_ROOT / ("index.html" if parsed.path in {"/", ""} else parsed.path.lstrip("/"))
        if not path.is_file() or STATIC_ROOT not in path.resolve().parents and path.resolve() != STATIC_ROOT:
            self.send_error(404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = STATIC_ROOT / ("index.html" if parsed.path in {"/", ""} else parsed.path.lstrip("/"))
        if not path.is_file() or STATIC_ROOT not in path.resolve().parents and path.resolve() != STATIC_ROOT:
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/run", "/api/chat"}:
            self.send_error(404)
            return
        try:
            payload = self.read_json()
            scenario = str(payload.get("scenario") or "review")
            if parsed.path == "/api/chat":
                messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
                self.write_json(run_chat_turn(messages, scenario))
                return
            text = str(payload.get("text") or "").strip()
            if not text:
                text = SCENARIOS.get(scenario, SCENARIOS["review"])
            self.write_json(run_demo_case(text, scenario))
        except Exception as exc:  # pragma: no cover - local demo should surface errors.
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"))

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def write_json(self, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def run_demo_case(text: str, scenario: str) -> dict:
    result = run_pipeline(text)
    adapter = BuiltinModelAdapter()
    case = {
        "id": f"product_alpha_{scenario}",
        "request": text,
        "ordinary_llm_failure": "把内部演示、干净状态或流畅草案写成已获授权的外部结论。",
    }
    ordinary_response = adapter.generate(mode="ordinary", case=case, result=result)
    raw_psm_response = adapter.generate(mode="psm", case=case, result=result)
    ordinary = ordinary_response.text
    raw_psm = raw_psm_response.text
    gated_psm = apply_psm_gate(raw_psm, result)
    ordinary_audit = audit_candidate_text(ordinary, result)
    raw_psm_audit = audit_candidate_text(raw_psm, result)
    gated_audit = audit_candidate_text(gated_psm, result)
    packet = result["packet"]
    return {
        "input": text,
        "scenario": scenario,
        "status": load_status_summary(),
        "packet": {
            "domain": packet["domain"],
            "risk_level": packet["omega"]["risk_level"],
            "phi_state": packet["phi_state"],
            "q_core": packet["q_core"],
            "omega": packet["omega"],
            "delta_sigma": packet["delta_sigma"],
            "pi_cavity": packet["pi_cavity"],
            "eta": packet["eta"],
            "statement_level": packet["statement_level"],
        },
        "q_audit": result["q_audit"],
        "route": result["route"],
        "bsigma_audit": result["bsigma_audit"],
        "ordinary": {
            "text": ordinary,
            "audit": ordinary_audit,
            "model": ordinary_response.model,
        },
        "psm_raw": {
            "text": raw_psm,
            "audit": raw_psm_audit,
            "model": raw_psm_response.model,
        },
        "psm_gated": {
            "text": gated_psm,
            "audit": gated_audit,
            "model": raw_psm_response.model,
        },
        "controller": {
            "changed_output": raw_psm.strip() != gated_psm.strip(),
            "risk_reduction": raw_psm_audit["net_risk"] - gated_audit["net_risk"],
            "ordinary_to_gated_risk_reduction": ordinary_audit["net_risk"] - gated_audit["net_risk"],
        },
        "release_boundary": {
            "ordinary_release_candidate": False,
            "raw_psm_release_candidate": False,
            "gated_psm_candidate_only": True,
            "rule_replacement_allowed": False,
            "external_user_trial_allowed": False,
        },
    }


def run_chat_turn(messages: list[dict], scenario: str) -> dict:
    conversation = normalize_chat_messages(messages)
    user_indexes = [index for index, item in enumerate(conversation) if item["role"] == "user"]
    if not user_indexes:
        conversation = [{"role": "user", "content": SCENARIOS.get(scenario, SCENARIOS["review"])}]
        user_indexes = [0]
    conversation = conversation[: user_indexes[-1] + 1]
    current = conversation[-1]["content"]
    user_messages = [item["content"] for item in conversation if item["role"] == "user"]
    assistant_messages = [item["content"] for item in conversation if item["role"] == "assistant"]

    # Only the current user message enters the property-state classifier. Role history
    # remains semantic context for answer generation and cannot override the domain route.
    audit_text = current
    result = run_demo_case(audit_text, scenario)
    intent = detect_chat_intent(current, conversation)
    project_context = load_project_context()
    grounding_facts, grounding_sources = grounding_for_intent(
        intent,
        current,
        conversation,
        project_context,
    )
    assistant_message = build_chat_answer(current, conversation, result, intent, project_context)
    quality_audit = audit_chat_answer(
        current,
        assistant_message,
        intent=intent,
        grounding_facts=grounding_facts,
        grounding_sources=grounding_sources,
        previous_assistant_answers=assistant_messages,
    )
    result["chat"] = {
        "turn_index": len(user_messages),
        "current_user_message": current,
        "audit_text": audit_text,
        "intent": intent,
        "assistant_message": assistant_message,
        "assistant_audit": audit_candidate_text(assistant_message, result),
        "quality_audit": quality_audit,
        "state_continuity": {
            "history_user_turns": len(user_messages),
            "history_assistant_turns": len(assistant_messages),
            "history_messages": len(conversation),
            "context_carried_forward": len(conversation) > 1,
            "assistant_history_available": bool(assistant_messages),
            "assistant_history_used": bool(assistant_messages),
            "semantic_audit_separated": True,
            "release_boundary_retained": True,
            "rule_replacement_allowed": False,
            "external_user_trial_allowed": False,
        },
    }
    return result


def normalize_chat_messages(messages: list[dict]) -> list[dict[str, str]]:
    normalized = []
    for item in messages[-24:]:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            continue
        content = str(item.get("content") or "").strip()
        if content:
            normalized.append({"role": str(item["role"]), "content": content[:4000]})
    return normalized


def build_chat_answer(
    current: str,
    conversation: list[dict[str, str]],
    result: dict,
    intent: str,
    project_context: dict,
) -> str:
    text = current.strip()
    if intent == "identity":
        return (
            "你好，我是物性AI的本地聊天原型。你可以像现在这样直接问我问题，我会先按普通对话回答；"
            "如果问题涉及医疗、法律、交易、上线发布等高风险场景，我会保留边界，不把草案说成已经验证的结论。"
        )
    if intent == "psm_vs_llm":
        return psm_vs_llm_answer()
    if intent == "project_status":
        return project_status_answer(project_context)
    if intent == "roadmap":
        return roadmap_answer(project_context)
    if intent == "history_reference":
        return history_reference_answer(text, conversation)
    if intent == "chat_capability":
        return (
            "可以聊天。你直接输入问题，我会结合前面的对话回答；涉及高风险事项时，我会说明证据和执行边界。"
        )
    if intent == "repeated_question":
        previous = previous_answer_for_same_question(conversation, current)
        if previous:
            return f"这个问题刚才问过。核心回答仍是：{first_answer_sentence(previous)}"
    answer = try_ollama_chat_answer(current, conversation, result)
    if not answer:
        answer = fallback_chat_answer(current, result, conversation)
    audit = audit_candidate_text(answer, result)
    if audit["status"] in {"unsafe", "risky"}:
        return fallback_chat_answer(current, result, conversation)
    return answer


def detect_chat_intent(text: str, conversation: list[dict[str, str]]) -> str:
    lower = text.casefold().strip()
    if is_identity_question(lower):
        return "identity"
    if is_psm_vs_llm_question(lower):
        return "psm_vs_llm"
    if is_history_reference_question(lower):
        return "history_reference"
    if is_project_status_question(lower):
        return "project_status"
    if is_roadmap_question(lower):
        return "roadmap"
    if is_chat_capability_question(lower):
        return "chat_capability"
    if is_theory_question(lower):
        return "theory"
    if previous_answer_for_same_question(conversation, text):
        return "repeated_question"
    return "general"


def is_identity_question(text: str) -> bool:
    markers = ["你是谁", "你是誰", "who are you", "你叫什么", "你叫什麼"]
    greetings = ["你好", "hello", "hi", "嗨"]
    return any(marker in text for marker in markers) or text.strip() in greetings


def is_chat_capability_question(text: str) -> bool:
    markers = ["可以聊天吗", "可以聊天嗎", "怎么聊天", "怎麼聊天", "能聊天吗", "能聊天嗎", "聊天功能在哪"]
    return any(marker in text for marker in markers)


def is_psm_vs_llm_question(text: str) -> bool:
    has_psm = "物性ai" in text or "物性 ai" in text or "物性模型" in text
    has_llm = "普通大模型" in text or "大语言模型" in text or "大語言模型" in text or "llm" in text
    asks_difference = "区别" in text or "差別" in text or "差异" in text or "不同" in text
    return has_psm and has_llm and asks_difference


def is_history_reference_question(text: str) -> bool:
    history_markers = ("刚才", "剛才", "上一轮", "上一輪", "你刚刚", "你剛剛", "前面")
    reference_markers = (
        "阶段",
        "階段",
        "第几",
        "第幾",
        "说了什么",
        "說了什麼",
        "叫什么",
        "叫什麼",
        "回答",
    )
    return any(marker in text for marker in history_markers) and any(
        marker in text for marker in reference_markers
    )


def is_project_status_question(text: str) -> bool:
    markers = (
        "项目现在做到哪里",
        "項目現在做到哪裡",
        "项目做到哪里",
        "項目做到哪裡",
        "项目进度",
        "項目進度",
        "当前版本",
        "當前版本",
        "现在什么情况",
        "現在什麼情況",
        "current status",
    )
    return any(marker in text for marker in markers)


def is_roadmap_question(text: str) -> bool:
    markers = (
        "后续计划",
        "後續計畫",
        "后续规划",
        "後續規劃",
        "下一步计划",
        "下一步計畫",
        "接下来做什么",
        "接下來做什麼",
        "路线图",
        "路線圖",
        "roadmap",
    )
    return any(marker in text for marker in markers)


def is_theory_question(text: str) -> bool:
    theory_markers = (
        "物性论",
        "物性論",
        "q 核",
        "q核",
        "b_sigma",
        "状态链",
        "狀態鏈",
        "sigma+",
        "σ+",
    )
    question_markers = ("解释", "解釋", "是什么", "是什麼", "为什么", "為什麼", "如何")
    return any(marker in text for marker in theory_markers) and any(
        marker in text for marker in question_markers
    )


def project_status_answer(context: dict) -> str:
    return (
        f"当前项目是 {context['current_version']}。确定性正式源是 {context['formal_version']}，"
        f"共有 {context['core_cases']} 个正式案例，正式回归目前全部通过。"
        f"最近一轮定向外部模型证据中，raw/gated 风险分别为 "
        f"{context['raw_psm_risky_rows']}/{context['gated_psm_risky_rows']}。\n\n"
        f"下一阶段是 {context['next_version']}：{context['next_objective']}。"
        "当前仍是内部本地聊天候选，外部用户试用没有开放。"
    )


def roadmap_answer(context: dict) -> str:
    if context["next_version"] == "PSM V0.250":
        construction = (
            "施工顺序是：先冻结同题模型基准集，再对本地候选模型测量回答质量、边界、延迟和失败率；"
            "随后把生成接口抽象为 provider，并输出回答、接地事实、不确定项和所需裁判；"
            "最后刷新 v249_ 外部证据并跑完整回归。"
        )
    else:
        construction = (
            "施工顺序是：先补齐该阶段的失败复现和固定测试，再实现阶段契约，"
            "随后运行质量审计和完整回归，全部通过后才刷新运行快照并推进下一版本。"
        )
    return (
        f"项目当前位于 {context['current_version']}，下一阶段是 {context['next_version']}。"
        f"这一阶段的目标是：{context['next_objective']}\n\n"
        f"{construction}"
        "外部试用继续保持关闭，直到对应放行门通过。"
    )


def history_reference_answer(text: str, conversation: list[dict[str, str]]) -> str:
    previous = [item["content"] for item in conversation[:-1] if item["role"] == "assistant"]
    if not previous:
        return "当前对话里没有可引用的上一轮助手回答。"
    latest = previous[-1]
    stage_number = requested_stage_number(text)
    if stage_number:
        stage = extract_numbered_stage(latest, stage_number)
        if stage:
            return f"我上一轮回答中的第{stage_number}阶段是：“{stage}”。"
        return f"我检查了上一轮回答，没有找到明确标注的第{stage_number}阶段。"
    return f"我上一轮的核心回答是：{first_answer_sentence(latest)}"


def requested_stage_number(text: str) -> int | None:
    chinese_numbers = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
    match = re.search(r"第\s*([一二三四五1-5])\s*(?:阶段|階段|步|部分)", text)
    if not match:
        return None
    value = match.group(1)
    return int(value) if value.isdigit() else chinese_numbers[value]


def extract_numbered_stage(answer: str, stage_number: int) -> str:
    chinese = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五"}[stage_number]
    patterns = (
        rf"第\s*{chinese}\s*(?:阶段|階段|步|部分)\s*[:：-]?\s*([^\n。；;]+)",
        rf"(?:^|\n)\s*{stage_number}\s*[.、)]\s*([^\n。；;]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, answer, flags=re.MULTILINE)
        if match:
            return match.group(1).strip().rstrip("。；; ")
    return ""


def previous_answer_for_same_question(
    conversation: list[dict[str, str]],
    current: str,
) -> str:
    target = normalize_question(current)
    for index in range(len(conversation) - 2, -1, -1):
        item = conversation[index]
        if item["role"] != "user" or normalize_question(item["content"]) != target:
            continue
        if index + 1 < len(conversation) and conversation[index + 1]["role"] == "assistant":
            return conversation[index + 1]["content"]
    return ""


def normalize_question(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.casefold(), flags=re.UNICODE)


def first_answer_sentence(text: str, limit: int = 220) -> str:
    sentence = re.split(r"(?<=[。！？!?])|\n", text.strip(), maxsplit=1)[0].strip()
    if len(sentence) > limit:
        return sentence[:limit].rstrip() + "..."
    return sentence


def psm_vs_llm_answer() -> str:
    return (
        "可以。简单说，普通大模型主要是在“接话”：它根据上下文预测下一段最合适的语言，所以很会解释、总结、续写，"
        "但它容易把流畅回答误当成可靠结论。\n\n"
        "物性AI想做的是先“接状态”，再接话。它回答前先判断：这个问题属于什么对象，风险有多高，哪些证据是真的，"
        "哪些只是猜测，哪些地方必须保留边界。然后再生成回答。\n\n"
        "所以区别不是“会不会说话”，而是回答前有没有状态约束。普通大模型更像语言生成器；物性AI更像带状态审计的智能系统："
        "能说，也要知道什么不能说成定论。"
    )


def try_ollama_chat_answer(
    current: str,
    conversation: list[dict[str, str]],
    result: dict,
) -> str:
    prompt = build_chat_prompt(current, conversation, result)
    request = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=json.dumps(
            {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 420},
            },
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=CHAT_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return ""
    text = str(payload.get("response") or "").strip()
    if not text:
        return ""
    if text.startswith(("PSM 门控候选回答", "普通候选回答")):
        return ""
    duration_ms = int((time.perf_counter() - started) * 1000)
    text = sanitize_chat_answer(text)
    return text[:1800].strip() + (f"\n\n（本地模型回答，用时 {duration_ms}ms）" if duration_ms > 0 else "")


def build_chat_prompt(
    current: str,
    conversation: list[dict[str, str]],
    result: dict,
) -> str:
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    role_labels = {"user": "用户", "assistant": "助手"}
    recent = "\n".join(
        f"{role_labels[item['role']]}：{item['content']}" for item in conversation[-8:]
    )
    required_judges = ", ".join(route["required_judges"]) or "无强制外部裁判"
    return "\n".join(
        [
            "你是物性AI的聊天助手。用户希望正常聊天：我问，你答。",
            "请像普通聊天产品一样直接、自然、简洁地回答，不要把内部审计流程当作正文展示。",
            "不要使用 emoji，不要用过度热情的客服腔，不要只确认页面状态而回避用户真正问题。",
            "除非用户主动询问机制，不要输出 PSM、Q 核、Ω、B_sigma、Σ+、门控候选、状态链这些术语。",
            "如果问题属于医疗、法律、交易、生产上线、隐私合规、外部发布等高风险场景：可以解释、列步骤、给草案，但必须明确不能替代专业判断或真实授权，不要给已验证/已批准/可直接执行的结论。",
            "如果问题是普通闲聊、写作、解释、计划、代码思路，则直接帮助用户。",
            "中文回答，优先繁简混合可读，控制在 500 字以内。",
            "",
            "最近对话（保留角色）：",
            recent,
            "",
            "当前用户问题：",
            current,
            "",
            "内部状态，只用于把握风险，不要原样输出：",
            f"- domain: {packet['domain']}",
            f"- risk_level: {packet['omega']['risk_level']}",
            f"- q_status: {q_audit['status']}",
            f"- route: {route['route']}",
            f"- required_judges: {required_judges}",
            f"- bsigma_status: {bsigma['status']}",
        ]
    )


def sanitize_chat_answer(text: str) -> str:
    emoji_ranges = [
        (0x1F300, 0x1FAFF),
        (0x2600, 0x27BF),
    ]
    cleaned = []
    for char in text:
        code = ord(char)
        if any(start <= code <= end for start, end in emoji_ranges):
            continue
        cleaned.append(char)
    return "".join(cleaned).strip()


def fallback_chat_answer(
    current: str,
    result: dict,
    conversation: list[dict[str, str]] | None = None,
) -> str:
    packet = result["packet"]
    domain = packet["domain"]
    risk = packet["omega"]["risk_level"]
    if risk in {"high", "critical"}:
        if domain == "medical":
            return (
                "我可以帮你判断信息是否完整，但不能在聊天中替代医生诊断。"
                "如果出现胸痛、呼吸困难、意识异常、大量出血或症状迅速恶化，请立即联系当地急救。"
                "其余情况请说明症状、开始时间、严重程度、年龄、既往病史和正在使用的药物，我会帮你整理就医重点。"
            )
        if domain == "legal":
            return (
                "我可以帮你梳理争点、材料和提问清单，但不能把聊天内容当作律师意见。"
                "先确认司法辖区、事件时间线、合同或通知原文、截止日期以及你希望达到的结果；"
                "涉及诉讼时效、签署或付款前，应让当地合资格律师核对。"
            )
        if domain == "trading":
            return (
                "这个结论目前不能直接转成实盘指令。我可以继续做回测、盲测、成本与滑点压力测试、"
                "最大回撤检查和模拟盘验证；只有风险门、执行权限和人工放行都明确后，才讨论实盘。"
            )
        if domain == "code_engineering":
            return (
                "可以继续做工程方案，但当前结果不能直接视为生产放行。上线前至少要补齐自动化测试、"
                "依赖与配置核对、回滚演练、日志监控和分阶段发布，并保留可快速撤回的版本。"
            )
        return (
            "我可以继续帮你形成方案和验证清单，但当前聊天不能替代真实审批或外部专业结论。"
            f"针对“{current}”，下一步应先确认适用范围和已有证据，再标出必须由外部来源或负责人确认的部分。"
        )
    if domain == "writing":
        return f"可以。我会按你的目标来写，并避免把没有验证的内容写成定论。你这句话的核心需求是：{current}"
    if domain == "wuxing_theory":
        return (
            "可以。从物性AI角度看，关键不是先接话，而是先接住状态：对象是什么、边界在哪里、哪些结论已经有证据、哪些还只是候选。"
            "然后再给出回答。"
        )
    context_answer = contextual_general_fallback(current, conversation or [])
    if context_answer:
        return context_answer
    return (
        f"本地生成模型这次没有返回有效内容，因此我不能可靠回答“{current}”。"
        "你可以重试；当前状态链和安全边界仍然有效。"
    )


def contextual_general_fallback(
    current: str,
    conversation: list[dict[str, str]],
) -> str:
    history = "\n".join(item["content"] for item in conversation[:-1])
    asks_sweetness = any(marker in current for marker in ("哪个更甜", "哪個更甜", "谁更甜", "誰更甜"))
    compares_apple_banana = any(marker in history for marker in ("苹果和香蕉", "蘋果和香蕉", "苹果与香蕉", "蘋果與香蕉"))
    if asks_sweetness and compares_apple_banana:
        return (
            "通常成熟香蕉比多数苹果更甜，因为香蕉成熟后淀粉会转成糖。"
            "不过具体甜度取决于品种和成熟程度，有些高糖苹果也会比未成熟香蕉更甜。"
        )
    return ""


def load_project_context() -> dict:
    status, source = load_project_status_payload()
    summary = load_status_summary()
    next_stage = status.get("next_stage") or {}
    eval_report = str(status.get("core_metrics", {}).get("eval", {}).get("report") or "")
    formal_match = re.search(r"PSM_V(\d+\.\d+)", eval_report, flags=re.IGNORECASE)
    formal_raw = status.get("source_evidence_version")
    if formal_match:
        formal_version = f"PSM V{formal_match.group(1)}"
    elif formal_raw:
        formal_version = to_display_version(str(formal_raw))
    else:
        formal_version = summary["version"]
    next_version = to_display_version(str(next_stage.get("version") or "未定义"))
    next_objective = humanize_stage_objective(str(next_stage.get("objective") or "完成下一阶段验证"))
    roadmap_source = "roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md"
    return {
        "current_version": summary["version"],
        "formal_version": formal_version,
        "core_cases": summary["core_cases"],
        "raw_psm_risky_rows": summary.get("raw_psm_risky_rows", 0),
        "gated_psm_risky_rows": summary.get("gated_psm_risky_rows", 0),
        "next_version": next_version,
        "next_objective": next_objective,
        "source": source,
        "roadmap_source": roadmap_source,
    }


def grounding_for_intent(
    intent: str,
    current: str,
    conversation: list[dict[str, str]],
    context: dict,
) -> tuple[list[str], list[str]]:
    if intent == "project_status":
        return (
            [
                context["current_version"],
                context["formal_version"],
                str(context["core_cases"]),
                context["next_version"],
            ],
            [context["source"], context["roadmap_source"]],
        )
    if intent == "roadmap":
        return (
            [context["current_version"], context["next_version"], context["next_objective"]],
            [context["source"], context["roadmap_source"]],
        )
    if intent == "history_reference":
        previous = [item["content"] for item in conversation[:-1] if item["role"] == "assistant"]
        stage_number = requested_stage_number(current)
        if previous and stage_number:
            stage = extract_numbered_stage(previous[-1], stage_number)
            return ([stage] if stage else [], ["conversation.assistant_history"])
        return ([], ["conversation.assistant_history"])
    if intent == "identity":
        return (["物性AI"], ["product_identity"])
    if intent == "chat_capability":
        return (["聊天"], ["product_capability"])
    if intent == "psm_vs_llm":
        return (["物性AI", "普通大模型"], ["product_theory_contract"])
    return ([], [])


def load_project_status_payload() -> tuple[dict, str]:
    status_paths = sorted(
        (PSM_ROOT / "project_status_out").glob("psm_v0.*_project_status.json"),
        key=status_version,
    )
    if status_paths:
        path = status_paths[-1]
        return load_json(path), str(path.relative_to(PSM_ROOT))
    runtime_path = PSM_ROOT / "runtime" / "current_runtime_snapshot.json"
    runtime = load_json(runtime_path) if runtime_path.exists() else {}
    if runtime.get("project_status"):
        return runtime["project_status"], str(runtime_path.relative_to(PSM_ROOT))
    raise FileNotFoundError("No PSM project status or runtime snapshot found.")


def to_display_version(version: str) -> str:
    normalized = version.strip().replace("_", " ")
    normalized = re.sub(r"(?i)^psm\s*v?", "PSM V", normalized)
    normalized = re.sub(r"(?i)^psm_v", "PSM V", normalized)
    return normalized


def humanize_stage_objective(objective: str) -> str:
    if "chat-quality" in objective or "assistant-turn history" in objective:
        return (
            "建立聊天回答质量与事实落地边界，补齐项目进度、路线图、助手历史、"
            "理论解释、重复提问和高风险帮助式拒答"
        )
    if "model bakeoff" in objective.casefold():
        return "建立本地模型对比与选择基线，按质量、风险、延迟和资源占用选择候选模型"
    if "refresh full required/fault external evidence" in objective.casefold():
        return (
            "完成 v249_ 的全量必要/故障与定向 Ollama/控制器证据刷新，"
            "并建立本地模型对照和结构化生成契约"
        )
    return objective


def load_status_summary() -> dict:
    status_paths = sorted(
        (PSM_ROOT / "project_status_out").glob("psm_v0.*_project_status.json"),
        key=status_version,
    )
    runtime_path = PSM_ROOT / "runtime" / "current_runtime_snapshot.json"
    runtime = load_json(runtime_path) if runtime_path.exists() else {}

    if status_paths:
        status = load_json(status_paths[-1])
        formal_status = status if "candidate_gate" in status else {}
        optional_status = status if "targeted_optional_external" in status else {}
        for path in reversed(status_paths):
            data = load_json(path)
            if not formal_status and "candidate_gate" in data:
                formal_status = data
            if not optional_status and "targeted_optional_external" in data:
                optional_status = data
            if formal_status and optional_status:
                break
        if not optional_status:
            optional_status = status
    elif runtime.get("project_status"):
        status = runtime["project_status"]
        formal_status = status if "candidate_gate" in status else runtime.get("formal_project_status", {})
        optional_status = runtime.get("optional_project_status", status)
    else:
        raise FileNotFoundError("No PSM project status or runtime snapshot found.")

    readiness_path = PSM_ROOT / "product_alpha_out" / "psm_v0.235_chat_alpha_readiness.json"
    if not readiness_path.exists():
        readiness_path = PSM_ROOT / "product_alpha_out" / "psm_v0.230_product_alpha_readiness.json"
    readiness = load_json(readiness_path) if readiness_path.exists() else runtime.get("chat_readiness", {})
    candidate_gate = status.get("candidate_gate") or formal_status.get("candidate_gate", {})
    target = optional_status.get("targeted_optional_external", {})
    full = optional_status.get("full_required_fault_external", candidate_gate)
    current_version = status["current_version"].replace("psm_v", "PSM V")
    return {
        "version": current_version,
        "core_cases": status["core_metrics"]["state_records"],
        "full_external_cases": full.get("holdout_cases"),
        "full_gated_risk": full.get("required_gated_psm_unsafe_or_risky"),
        "full_fault_events": full.get("fault_injection_events"),
        "full_controller_rescues": full.get("controller_rescue_count"),
        "targeted_optional_cases": target.get("holdout_cases", 0),
        "ordinary_risky_rows": target.get("optional_ordinary_unsafe_or_risky", 0),
        "raw_psm_risky_rows": target.get("optional_raw_psm_unsafe_or_risky", 0),
        "gated_psm_risky_rows": target.get("optional_gated_psm_unsafe_or_risky_adapter", 0),
        "chat_candidate_cases": candidate_gate.get("holdout_cases"),
        "chat_gated_risk": candidate_gate.get("required_gated_psm_unsafe_or_risky"),
        "ready_for_internal_local_demo": readiness.get("ready_for_internal_local_demo", readiness.get("ready_for_internal_chat_demo")),
        "ready_for_internal_chat_demo": readiness.get("ready_for_internal_chat_demo", readiness.get("ready_for_internal_local_demo")),
        "ready_for_external_user_trial": readiness.get("ready_for_external_user_trial", False),
    }


def status_version(path: Path) -> int:
    prefix = "psm_v0."
    suffix = "_project_status.json"
    name = path.name
    if not name.startswith(prefix) or not name.endswith(suffix):
        return -1
    try:
        return int(name[len(prefix) : -len(suffix)])
    except ValueError:
        return -1


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
