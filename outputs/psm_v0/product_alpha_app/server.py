from __future__ import annotations

import argparse
import json
import mimetypes
import os
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
    user_messages = [
        str(item.get("content") or "").strip()
        for item in messages
        if item.get("role") == "user" and str(item.get("content") or "").strip()
    ]
    if not user_messages:
        user_messages = [SCENARIOS.get(scenario, SCENARIOS["review"])]
    current = user_messages[-1]
    context_tail = "；".join(user_messages[-4:])
    audit_text = current
    if len(user_messages) > 1:
        audit_text = (
            f"多轮聊天 history：{context_tail}\n"
            f"本轮请求：{current}\n"
            "要求：继承上一轮 Q 核、外部裁判、失败入账和 release boundary。"
        )
    result = run_demo_case(audit_text, scenario)
    assistant_message = build_chat_answer(current, user_messages, result)
    result["chat"] = {
        "turn_index": len(user_messages),
        "current_user_message": current,
        "audit_text": audit_text,
        "assistant_message": assistant_message,
        "assistant_audit": audit_candidate_text(assistant_message, result),
        "state_continuity": {
            "history_user_turns": len(user_messages),
            "context_carried_forward": len(user_messages) > 1,
            "release_boundary_retained": True,
            "rule_replacement_allowed": False,
            "external_user_trial_allowed": False,
        },
    }
    return result


def build_chat_answer(current: str, user_messages: list[str], result: dict) -> str:
    text = current.strip()
    lower = text.lower()
    if is_identity_question(lower):
        return (
            "你好，我是物性AI的本地聊天原型。你可以像现在这样直接问我问题，我会先按普通对话回答；"
            "如果问题涉及医疗、法律、交易、上线发布等高风险场景，我会保留边界，不把草案说成已经验证的结论。"
        )
    if is_psm_vs_llm_question(lower):
        return psm_vs_llm_answer()
    if is_chat_capability_question(lower):
        return (
            "可以，现在这个页面应该就是正常聊天模式：你输入问题，我直接回答。"
            "右侧或下方的调试详情只是给研发看的，不再作为主要回答。"
        )
    answer = try_ollama_chat_answer(current, user_messages, result)
    if not answer:
        answer = fallback_chat_answer(current, result)
    audit = audit_candidate_text(answer, result)
    if audit["status"] in {"unsafe", "risky"}:
        return fallback_chat_answer(current, result)
    return answer


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


def psm_vs_llm_answer() -> str:
    return (
        "可以。简单说，普通大模型主要是在“接话”：它根据上下文预测下一段最合适的语言，所以很会解释、总结、续写，"
        "但它容易把流畅回答误当成可靠结论。\n\n"
        "物性AI想做的是先“接状态”，再接话。它回答前先判断：这个问题属于什么对象，风险有多高，哪些证据是真的，"
        "哪些只是猜测，哪些地方必须保留边界。然后再生成回答。\n\n"
        "所以区别不是“会不会说话”，而是回答前有没有状态约束。普通大模型更像语言生成器；物性AI更像带状态审计的智能系统："
        "能说，也要知道什么不能说成定论。"
    )


def try_ollama_chat_answer(current: str, user_messages: list[str], result: dict) -> str:
    prompt = build_chat_prompt(current, user_messages, result)
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


def build_chat_prompt(current: str, user_messages: list[str], result: dict) -> str:
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    recent = "\n".join(f"- {item}" for item in user_messages[-4:])
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
            "最近用户消息：",
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


def fallback_chat_answer(current: str, result: dict) -> str:
    packet = result["packet"]
    domain = packet["domain"]
    risk = packet["omega"]["risk_level"]
    if risk in {"high", "critical"}:
        return (
            "可以，我先给你一个带边界的回答：这个问题属于较高风险场景，我能帮你整理思路、检查条件、列出下一步验证清单，"
            "但不能把当前聊天内容当成已经获得外部授权或专业结论。\n\n"
            f"针对你的问题：{current}\n\n"
            "建议先分三步推进：1. 明确目标和适用范围；2. 列出需要真实证据或专业确认的部分；3. 再生成可执行草案或检查清单。"
        )
    if domain == "writing":
        return f"可以。我会按你的目标来写，并避免把没有验证的内容写成定论。你这句话的核心需求是：{current}"
    if domain == "wuxing_theory":
        return (
            "可以。从物性AI角度看，关键不是先接话，而是先接住状态：对象是什么、边界在哪里、哪些结论已经有证据、哪些还只是候选。"
            "然后再给出回答。"
        )
    return f"可以。我的理解是：你想让我直接回应“{current}”。我会按正常聊天方式回答；如果涉及高风险结论，我会同时保留必要边界。"


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
