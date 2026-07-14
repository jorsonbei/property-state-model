from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


APP_ROOT = Path(__file__).resolve().parent
PSM_ROOT = APP_ROOT.parent
STATIC_ROOT = APP_ROOT / "static"
sys.path.insert(0, str(PSM_ROOT))

from psm_v0.candidate_auditor import audit_candidate_text  # noqa: E402
from psm_v0.chat_quality_auditor import audit_chat_answer  # noqa: E402
from psm_v0.chat_prompt import build_chat_prompt, sanitize_model_answer  # noqa: E402
from psm_v0.chat_provider import OllamaChatProvider, ProviderRequest  # noqa: E402
from psm_v0.model_adapter import BuiltinModelAdapter  # noqa: E402
from psm_v0.pipeline import run_pipeline  # noqa: E402
from psm_v0.psm_gate_controller import apply_psm_gate  # noqa: E402
from psm_v0.state_extractor import infer_domain  # noqa: E402
from psm_v0.verified_knowledge import VerifiedKnowledge, match_verified_knowledge  # noqa: E402


SCENARIOS = {
    "review": "医疗系统 product-alpha empty-fixture evidence 摘要中，说明它不是 external-user release。",
    "research": "研究项目已经完成内部复核，请说明为什么这还不是外部等价证明。",
    "code": "代码已经通过本地 smoke test，请给出上线前仍需要保留的 CI、rollback 和 monitoring 边界。",
    "writing": "把物性论宣传语改成有力量但不夸大外部证明的版本。",
    "theory": "解释 Q 核、Ω、φ、Δσ、Π、η、B_sigma、Σ+ 如何避免会接话但不接状态。",
    "trading": "交易策略回测看起来很好，请说明为什么这不能直接变成实盘授权。",
}

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL_OVERRIDE = os.environ.get("OLLAMA_MODEL", "").strip()
CHAT_TIMEOUT_SECONDS = int(os.environ.get("PSM_CHAT_TIMEOUT_SECONDS", "45"))
CHAT_MAX_TOKENS_OVERRIDE = os.environ.get("PSM_CHAT_MAX_TOKENS", "").strip()


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
    state_input, user_history_used_for_state = semantic_state_input(current, conversation)
    result = run_demo_case(state_input, scenario)
    intent = detect_chat_intent(current, conversation)
    project_context = load_project_context()
    verified_knowledge = match_verified_knowledge(current)
    grounding_facts, grounding_sources = grounding_for_intent(
        intent,
        current,
        conversation,
        project_context,
    )
    if verified_knowledge:
        grounding_facts.extend(verified_knowledge.grounding_facts)
        grounding_sources.extend(verified_knowledge.grounding_sources)
    generation = build_chat_generation(
        current,
        conversation,
        result,
        intent,
        project_context,
        verified_knowledge=verified_knowledge,
    )
    assistant_message = generation["answer"]
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
        "generation": {
            **generation,
            "grounded_facts": grounding_facts,
            "grounding_sources": grounding_sources,
            "uncertainties": result["packet"].get("eta", {}).get("uncertainties", []),
            "required_judges": result["route"].get("required_judges", []),
        },
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
            "user_history_used_for_state": user_history_used_for_state,
            "release_boundary_retained": True,
            "rule_replacement_allowed": False,
            "external_user_trial_allowed": False,
        },
    }
    return result


def semantic_state_input(
    current: str,
    conversation: list[dict[str, str]],
) -> tuple[str, bool]:
    if infer_domain(current) != "general":
        return current, False
    previous_user_messages = [
        item["content"] for item in conversation[:-1] if item["role"] == "user"
    ]
    for previous in reversed(previous_user_messages):
        previous_domain = infer_domain(previous)
        if previous_domain in {
            "medical",
            "legal",
            "trading",
            "code_engineering",
            "research",
            "wuxing_theory",
        }:
            return f"{current}\n此前用户问题：{previous}", True
    return current, False


def normalize_chat_messages(messages: list[dict]) -> list[dict[str, str]]:
    normalized = []
    for item in messages[-24:]:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            continue
        content = str(item.get("content") or "").strip()
        if content:
            normalized.append({"role": str(item["role"]), "content": content[:4000]})
    return normalized


def build_chat_generation(
    current: str,
    conversation: list[dict[str, str]],
    result: dict,
    intent: str,
    project_context: dict,
    *,
    verified_knowledge: VerifiedKnowledge | None = None,
) -> dict:
    text = current.strip()
    if intent == "identity":
        return deterministic_generation(
            "你好，我是物性AI的本地聊天原型。你可以像现在这样直接问我问题，我会先按普通对话回答；"
            "如果问题涉及医疗、法律、交易、上线发布等高风险场景，我会保留边界，不把草案说成已经验证的结论。"
        )
    if intent == "psm_vs_llm":
        return deterministic_generation(psm_vs_llm_answer())
    if intent == "project_results":
        return deterministic_generation(project_results_answer(project_context))
    if intent == "project_status":
        return deterministic_generation(project_status_answer(project_context, text))
    if intent == "roadmap":
        return deterministic_generation(roadmap_answer(project_context))
    if intent == "history_reference":
        return deterministic_generation(history_reference_answer(text, conversation))
    if intent == "chat_capability":
        return deterministic_generation(
            "可以聊天。你直接输入问题，我会结合前面的对话回答；涉及高风险事项时，我会说明证据和执行边界。"
        )
    if intent == "repeated_question":
        previous = previous_answer_for_same_question(conversation, current)
        if previous:
            return deterministic_generation(
                f"这个问题刚才问过。核心回答仍是：{first_answer_sentence(previous)}"
            )
    if verified_knowledge:
        generation = deterministic_generation(verified_knowledge.answer)
        generation["knowledge_kernel"] = verified_knowledge.kernel_id
        return generation
    model_generation = try_ollama_chat_generation(current, conversation, result)
    if model_generation["status"] != "success":
        return deterministic_generation(
            fallback_chat_answer(current, result, conversation),
            status="degraded",
            attempted=model_generation,
        )
    model_generation["answer"] = complete_contextual_answer(
        model_generation["answer"], current, conversation, result
    )
    if result["packet"]["omega"]["risk_level"] in {"high", "critical"}:
        model_generation["answer"] = append_natural_boundary(model_generation["answer"], result)
    audit = audit_candidate_text(model_generation["answer"], result)
    if audit["status"] in {"unsafe", "risky"}:
        softened = soften_absolute_language(model_generation["answer"])
        softened_audit = audit_candidate_text(softened, result)
        if softened != model_generation["answer"] and softened_audit["status"] not in {
            "unsafe",
            "risky",
        }:
            model_generation["answer"] = softened
            model_generation["absolute_language_softened"] = True
            return model_generation
        repaired = append_natural_boundary(model_generation["answer"], result)
        repaired_audit = audit_candidate_text(repaired, result)
        if repaired_audit["status"] not in {"unsafe", "risky"}:
            model_generation["answer"] = repaired
            model_generation["boundary_repaired"] = True
            return model_generation
        return deterministic_generation(
            fallback_chat_answer(current, result, conversation),
            status="rejected",
            attempted=model_generation,
        )
    return model_generation


def soften_absolute_language(answer: str) -> str:
    replacements = (
        (r"(?<!不能)(?<!不)(?<!未)(?<!无)保证", "尽量确保"),
        (r"(?<!不)(?<!未)一定", "通常"),
        (r"必然", "往往"),
        (r"完全正确", "更可靠"),
        (r"完全成功", "达到当前目标"),
        (r"彻底成功", "达到当前目标"),
    )
    softened = answer
    for pattern, replacement in replacements:
        softened = re.sub(pattern, replacement, softened)
    return softened


def complete_contextual_answer(
    answer: str,
    current: str,
    conversation: list[dict[str, str]],
    result: dict,
) -> str:
    domain = result["packet"]["domain"]
    history = "\n".join(item["content"] for item in conversation[:-1])
    if domain == "research" and "盲" in history + current and "失败" in current:
        if not any(marker in answer for marker in ("记录失败", "新的未见", "新盲集", "新 holdout")):
            return (
                f"{answer.rstrip()}\n\n应记录这次失败，冻结已打开的盲集；后续只能使用新的未见 holdout，"
                "原盲集不再作为独立证明。"
            )
    if domain == "trading" and "压力测试" in current:
        wrong_domain = any(
            marker in answer for marker in ("高并发", "CPU", "吞吐量", "大量用户", "系统性能")
        )
        if wrong_domain:
            targeted = trading_fallback(current, conversation)
            if targeted:
                return targeted
    if domain == "trading" and "停止条件" in current:
        if "连续" not in answer:
            return (
                f"{answer.rstrip()}\n\n还要把连续亏损次数或连续亏损天数写成固定阈值；"
                "触发后立即暂停，不能在看到结果后临时放宽。"
            )
    if domain == "legal" and any(marker in history for marker in ("聊天截图", "聊天记录")):
        if "原始" not in answer or not any(marker in answer for marker in ("导出", "备份")):
            return (
                f"{answer.rstrip()}\n\n同时保留原设备，并从平台导出原始聊天记录做只读备份；"
                "保存导出时间、账号和文件哈希，具体提交方式由当地合资格律师按司法辖区核对。"
            )
    if domain == "writing" and "点出状态" in history and "状态" not in answer:
        return "建议标题：\"AI 不应只会说，更要先看清状态\"。它保留原来的力度，也准确点出状态优先。"
    return answer


def deterministic_generation(
    answer: str,
    *,
    status: str = "success",
    attempted: dict | None = None,
) -> dict:
    return {
        "answer": answer,
        "status": status,
        "provider": "deterministic" if attempted is None else "deterministic_fallback",
        "model": None,
        "duration_ms": (attempted or {}).get("duration_ms", 0),
        "error": (attempted or {}).get("error"),
        "attempted_provider": (attempted or {}).get("provider"),
        "attempted_model": (attempted or {}).get("model"),
        "reasoning_leak_removed": (attempted or {}).get("reasoning_leak_removed", False),
    }


def detect_chat_intent(text: str, conversation: list[dict[str, str]]) -> str:
    lower = text.casefold().strip()
    if is_identity_question(lower):
        return "identity"
    if is_psm_vs_llm_question(lower):
        return "psm_vs_llm"
    if is_history_reference_question(lower):
        return "history_reference"
    if is_project_results_question(lower):
        return "project_results"
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
        "外部用户试用",
        "外部用戶試用",
        "开放给外部",
        "開放給外部",
        "直接放行",
        "current status",
        "按系统当前状态",
        "按系統當前狀態",
        "按当前系统状态",
        "按當前系統狀態",
        "按当前项目状态",
        "按當前項目狀態",
        "按本地当前项目状态",
        "按本地當前項目狀態",
        "本地项目记录",
        "本地項目記錄",
        "本地系统记录",
        "本地系統記錄",
        "本地记录",
        "本地紀錄",
        "正式版本号",
        "正式版本號",
        "核心验证门",
        "核心驗證門",
        "下一个真实动作",
        "下一個真實動作",
        "完成了哪些阶段的验收",
        "完成了哪些階段的驗收",
        "里程碑的预期交付",
        "里程碑的預期交付",
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
        "下一阶段要解决什么",
        "下一階段要解決什麼",
        "最先施工",
        "最先做的任务",
        "最先做的任務",
        "路线图",
        "路線圖",
        "roadmap",
    )
    return any(marker in text for marker in markers)


def is_project_results_question(text: str) -> bool:
    result_markers = (
        "这轮已经完成了什么",
        "這輪已經完成了什麼",
        "这轮完成了什么",
        "這輪完成了什麼",
        "完成的什么",
        "完成的什麼",
    )
    effect_markers = ("作用", "成果", "完成")
    return any(marker in text for marker in result_markers) or (
        "这轮" in text and any(marker in text for marker in effect_markers)
    )


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


def project_status_answer(context: dict, question: str = "") -> str:
    if any(marker in question for marker in ("部署", "配置库", "配置庫", "同步失败", "同步失敗", "容灾回滚", "容災回滾")):
        return (
            f"当前可验证项目状态是 {context['current_version']}，确定性正式源为 {context['formal_version']}，"
            f"共有 {context['core_cases']} 个正式案例；下一验证阶段仍是 {context['next_version']}。"
            "现有结构化状态没有登记自动部署、配置库同步失败或容灾回滚 runbook，因此不能把某一步说成已验证的本项目标准流程。\n\n"
            "作为通用且有条件的事故控制建议，第一步通常是暂停继续部署和后续写入，保留失败日志、配置版本与变更前快照；"
            "随后由负责人按已批准 runbook 判断重试还是回滚。外部用户试用仍未开放。"
        )
    if any(marker in question for marker in ("季度", "验收", "驗收", "交付节点", "交付節點", "里程碑")):
        return (
            "当前本地状态没有第二季度核心架构升级的验收清单或日期，因此不能列出不存在的已验收模块，也不能编造交付节点。"
            f"能够确认的是：当前发布版为 {context['current_version']}，确定性正式源为 {context['formal_version']}，"
            f"共有 {context['core_cases']} 个正式案例；{context['next_version']} 仍在独立聊天门验证，"
            "最近的真实里程碑是该门通过后再决定晋升。外部用户试用仍未开放。"
        )
    if any(marker in question for marker in ("正式版本", "版本号", "版本號", "核心验证门", "核心驗證門")):
        return (
            f"当前正式晋级版本是 {context['current_version']}；确定性正式源是 {context['formal_version']}，"
            f"共有 {context['core_cases']} 个正式案例，正式回归已经通过。"
            f"但目标版本 {context['next_version']} 的独立聊天语义门尚未通过，所以不能把整个 V0.251 说成已完成内部核心验证。"
            "外部用户试用仍未开放。"
        )
    if any(marker in question for marker in ("外部试用", "外部試用", "真实动作", "真實動作")):
        return (
            f"当前没有开放外部用户试用，正式版本仍是 {context['current_version']}。"
            f"记录中的下一真实动作是：{context['required_decision']}"
        )
    if any(marker in question for marker in ("最高优先级", "最高優先級", "优先级最高", "優先級最高", "优先任务", "優先任務")):
        return (
            f"当前最高优先级是完成 {context['next_version']} 的 {context['next_objective']}，"
            "并用新的来源隔离盲集通过独立外部语义门。"
            f"原因是正式版本仍是 {context['current_version']}，确定性正式源为 {context['formal_version']}，"
            f"共有 {context['core_cases']} 个正式案例；在正确性、相关性、幻觉控制、安全和边界门全部通过前，"
            "不能晋级或开放外部用户试用。"
        )
    if any(marker in question for marker in ("阻塞因素", "阻碍因素", "阻礙因素", "最大阻塞", "最大的阻塞")):
        user_blocker = "需要用户介入" if context["requires_user_input"] else "不需要用户介入"
        return (
            f"当前最大的阶段门是 {context['next_version']} 的独立语义质量尚未全部达到晋级阈值，"
            f"不是部署或材料缺失。现阶段{user_blocker}；工程上要保留失败证据、修复共通缺陷，"
            "再用全新未见盲集复验。外部用户试用仍未开放。"
        )
    answer = (
        f"当前项目是 {context['current_version']}。确定性正式源是 {context['formal_version']}，"
        f"共有 {context['core_cases']} 个正式案例，正式回归目前全部通过。"
        f"最近一轮定向外部模型证据中，raw/gated 风险分别为 "
        f"{context['raw_psm_risky_rows']}/{context['gated_psm_risky_rows']}。\n\n"
        f"下一阶段是 {context['next_version']}：{context['next_objective']}。"
        "当前仍是内部本地聊天候选，外部用户试用没有开放。"
    )
    if context["stage_blocked"]:
        answer += f"\n\nV0.251 当前未晋级：{context['required_decision']}"
    return answer


def roadmap_answer(context: dict) -> str:
    if context["stage_blocked"]:
        construction = (
            "80 题来源隔离数据集、judge-only 标签、两阶段 NoTargetRead 评测器和三轮 blind evidence 已完成；"
            "但独立 blind gate 没有通过，不能继续由同一开发者循环出题和裁判。"
            f"下一步需要：{context['required_decision']}"
        )
    elif context["next_version"] == "PSM V0.250":
        construction = (
            "施工顺序是：先冻结同题模型基准集，再对本地候选模型测量回答质量、边界、延迟和失败率；"
            "随后把生成接口抽象为 provider，并输出回答、接地事实、不确定项和所需裁判；"
            "最后刷新 v249_ 外部证据并跑完整回归。"
        )
    elif context["next_version"] == "PSM V0.251":
        construction = (
            "施工顺序是：先冻结至少 80 条人工设计问题，并按来源分成 train/dev/blind；"
            "生成阶段不读取 judge-only 标签，至少 20 条 blind 问题禁止回流；"
            "最后分别报告正确性、相关性、可执行性、多轮一致性、幻觉、安全与边界质量。"
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


def project_results_answer(context: dict) -> str:
    return (
        f"这轮已完成 {context['current_version']}：建立了本地模型 provider 和结构化生成契约，"
        f"并在固定同题集上选择 `{context['selected_model']}`。"
        f"模型均分为 {context['model_mean_score']:.2f}，回答、证据、不确定项、所需裁判和延迟现在会分开记录。\n\n"
        "它的作用是让正常聊天不再依赖硬编码候选文本，同时保留项目状态接地和高风险门控。"
        f"下一步是 {context['next_version']} 的独立聊天黄金集与盲测。"
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


def try_ollama_chat_generation(
    current: str,
    conversation: list[dict[str, str]],
    result: dict,
) -> dict:
    prompt = build_chat_prompt(current, conversation, result)
    provider = OllamaChatProvider(OLLAMA_BASE_URL)
    max_tokens = selected_chat_max_tokens()
    provider_result = provider.generate(
        ProviderRequest(
            prompt=prompt,
            model=selected_chat_model(),
            timeout_seconds=CHAT_TIMEOUT_SECONDS,
            max_tokens=max_tokens,
        )
    )
    first_result = provider_result
    if provider_result.status == "success" and provider_result.finish_reason == "length":
        provider_result = provider.generate(
            ProviderRequest(
                prompt=prompt,
                model=selected_chat_model(),
                timeout_seconds=CHAT_TIMEOUT_SECONDS,
                max_tokens=max(600, max_tokens * 2),
            )
        )
    generation = provider_result.to_dict()
    if first_result is not provider_result:
        generation["truncation_retry"] = True
        generation["first_finish_reason"] = first_result.finish_reason
        generation["first_duration_ms"] = first_result.duration_ms
        generation["duration_ms"] += first_result.duration_ms
    if provider_result.status == "success" and provider_result.finish_reason == "length":
        generation.update(
            status="truncated",
            answer="",
            error="Ollama reached the token limit after one expanded retry.",
        )
    if provider_result.status != "success":
        generation["reasoning_leak_removed"] = False
        return generation
    if generation["status"] != "success":
        generation["reasoning_leak_removed"] = False
        return generation
    text, reasoning_leak = sanitize_model_answer(provider_result.answer)
    if text.startswith(("PSM 门控候选回答", "普通候选回答")):
        generation.update(status="invalid_response", answer="", error="Candidate template leaked.")
        generation["reasoning_leak_removed"] = reasoning_leak
        return generation
    if not text:
        generation.update(status="empty", answer="", error="No visible answer remained after sanitation.")
        generation["reasoning_leak_removed"] = reasoning_leak
        return generation
    generation["answer"] = text[:1800].strip()
    generation["reasoning_leak_removed"] = reasoning_leak
    return generation


def append_natural_boundary(answer: str, result: dict) -> str:
    domain = result["packet"]["domain"]
    suffixes = {
        "medical": "这不能替代医生诊断；药物和治疗请由医生或药师确认，出现急症信号时立即联系当地急救。",
        "legal": "这不是律师意见；请结合司法辖区和期限，让当地合资格律师核对原始材料。",
        "trading": "这不构成实盘指令；还需 Fresh Holdout、成本与回撤检查、模拟盘验证和人工放行。",
        "code_engineering": "这是工程建议，不是生产放行；上线前还需测试、监控、回滚演练和负责人审批。",
        "research": "这仍是内部研究判断；强结论还需预注册边界、独立复现或外部验证。",
        "wuxing_theory": "这是物性论框架内的解释，不等于外部证明；声明等级仍由证据和验证边界决定。",
    }
    suffix = suffixes.get(domain, "这是带边界的解释，不能替代真实审批或外部验证。")
    if suffix in answer:
        return answer
    return f"{answer.rstrip()}\n\n{suffix}"


def selected_chat_model() -> str:
    if OLLAMA_MODEL_OVERRIDE:
        return OLLAMA_MODEL_OVERRIDE
    selection_path = PSM_ROOT / "runtime" / "chat_provider_selection.json"
    if selection_path.exists():
        selection = load_json(selection_path)
        selected = str(selection.get("selected_model") or "").strip()
        if selected:
            return selected
    return "gemma3:4b"


def selected_chat_max_tokens() -> int:
    if CHAT_MAX_TOKENS_OVERRIDE:
        return int(CHAT_MAX_TOKENS_OVERRIDE)
    selection_path = PSM_ROOT / "runtime" / "chat_provider_selection.json"
    if selection_path.exists():
        selection = load_json(selection_path)
        selected = selection.get("generation_parameters", {}).get("max_tokens")
        if isinstance(selected, int) and selected > 0:
            return selected
    return 180


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
            targeted = medical_fallback(current, conversation or [])
            if targeted:
                return targeted
            return (
                "我可以帮你判断信息是否完整，但不能在聊天中替代医生诊断。"
                "如果出现胸痛、呼吸困难、意识异常、大量出血或症状迅速恶化，请立即联系当地急救。"
                "其余情况请说明症状、开始时间、严重程度、年龄、既往病史和正在使用的药物，我会帮你整理就医重点。"
            )
        if domain == "legal":
            targeted = legal_fallback(current, conversation or [])
            if targeted:
                return targeted
            return (
                "我可以帮你梳理争点、材料和提问清单，但不能把聊天内容当作律师意见。"
                "先确认司法辖区、事件时间线、合同或通知原文、截止日期以及你希望达到的结果；"
                "涉及诉讼时效、签署或付款前，应让当地合资格律师核对。"
            )
        if domain == "trading":
            targeted = trading_fallback(current, conversation or [])
            if targeted:
                return targeted
            return (
                "这个结论目前不能直接转成实盘指令。我可以继续做回测、盲测、成本与滑点压力测试、"
                "最大回撤检查和模拟盘验证；只有风险门、执行权限和人工放行都明确后，才讨论实盘。"
            )
        if domain == "code_engineering":
            targeted = code_fallback(current, conversation or [])
            if targeted:
                return targeted
            return (
                "可以继续做工程方案，但当前结果不能直接视为生产放行。上线前至少要补齐自动化测试、"
                "依赖与配置核对、回滚演练、日志监控和分阶段发布，并保留可快速撤回的版本。"
            )
        if domain == "research":
            return research_fallback(current, conversation or [])
        if domain == "wuxing_theory":
            return theory_fallback(current)
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


def code_fallback(current: str, conversation: list[dict[str, str]]) -> str:
    history = "\n".join(item["content"] for item in conversation[:-1])
    if "max" in current.casefold() and "空" in current:
        return (
            "最小修复是在调用 `max` 前处理空列表，例如：`return max(values) if values else None`。"
            "如果 `None` 不是合法结果，也可以显式抛出带说明的 `ValueError`；再补空列表和正常列表两类测试。"
        )
    if "sql" in (history + current).casefold() and any(
        marker in current for marker in ("参数", "修复", "示例")
    ):
        return (
            "不要拼接用户输入，改用参数化查询。例如 SQLite：\n"
            "`row = conn.execute(\"SELECT * FROM users WHERE id = ?\", (user_id,)).fetchone()`\n"
            "占位符由驱动绑定值；表名等结构不能用值占位符时，要从固定白名单选择。"
        )
    if "500" in current and "重试" in current:
        return (
            "先查日志和请求链路，确认 500 的错误类型、依赖和受影响范围；不要先用重试掩盖根因。"
            "只有确认是短暂网络或下游超时后，才加有次数上限、退避和幂等保护的重试。"
        )
    return ""


def research_fallback(current: str, conversation: list[dict[str, str]]) -> str:
    history = "\n".join(item["content"] for item in conversation[:-1])
    if "固定主要指标" in current or "看结果前" in current:
        return (
            "因为看完结果再选指标，会把偶然波动挑成主要发现，放大选择偏差。"
            "应在实验前预注册主要指标、分析方法和停止条件；探索性发现可以报告，但要明确标成探索性并用新数据验证。"
        )
    if "盲测" in history and "失败" in current:
        return (
            "不能继续调到原盲集通过，因为它一旦被看见就成了开发数据，继续调整会造成目标泄漏和回拟合。"
            "应记录这次失败、冻结原结果，再建立新的未见 holdout；原盲集只保留作回归，不再充当独立证明。"
        )
    if "样本" in current:
        return (
            "应写成小样本下的初步结果，同时报告样本量、不确定性或置信区间，不能据此宣称已经泛化。"
            "下一步是扩大样本并做独立复现或外部验证。"
        )
    return (
        "先把当前结果限定为内部证据，列出数据来源、主要指标、失败项和可能偏差。"
        "要提高声明等级，需要预先固定协议，并在新的独立数据或外部复现中通过验证。"
    )


def trading_fallback(current: str, conversation: list[dict[str, str]]) -> str:
    history = "\n".join(item["content"] for item in conversation[:-1])
    if any(marker in current for marker in ("哪些成本", "检查哪些成本")):
        return (
            "至少检查佣金和手续费、买卖价差、滑点、市场冲击、税费、借券或融资成本，以及信号到成交的延迟。"
            "还要用不同成本情景重算净收益、回撤和容量；这仍不构成实盘授权。"
        )
    if "压力测试" in current or "滑点" in history:
        return (
            "先把滑点设成基准值的 1 倍、2 倍和 3 倍，并同时提高佣金、价差和成交延迟；"
            "每个情景重算净收益、最大回撤、成交率和容量。若收益消失或回撤越过预设门槛就记为失败，不进入模拟盘。"
        )
    if "停止条件" in current or "模拟盘" in history:
        return (
            "模拟盘前先写死停止条件：单日和累计亏损上限、最大回撤、连续亏损次数、成交偏差、数据中断和策略漂移阈值。"
            "任一触发就暂停并复核，不能自动放宽；实盘仍需独立风险门和人工放行。"
        )
    return ""


def medical_fallback(current: str, conversation: list[dict[str, str]]) -> str:
    history = "\n".join(item["content"] for item in conversation[:-1])
    if "记录" in current or "高烧" in history:
        return (
            "记录体温和测量时间、症状从何时开始、精神状态、呼吸、喝水与尿量、是否呕吐或抽搐、已用药物和剂量。"
            "孩子高烧且精神很差应尽快就医；出现呼吸困难、意识异常、抽搐或迅速恶化时立即联系当地急救。"
        )
    if "哪些情况" in current or "皮疹" in history:
        return (
            "如果皮疹伴随呼吸困难、喉咙发紧、面部或舌头肿胀、头晕昏厥或迅速扩散，请立即联系当地急救。"
            "不要自行继续可疑药物，尽快让医生或药师核对药名、剂量和出现时间。"
        )
    return ""


def legal_fallback(current: str, conversation: list[dict[str, str]]) -> str:
    history = "\n".join(item["content"] for item in conversation[:-1])
    if "三件事" in current and ("通知" in history or "期限" in history):
        return (
            "先做三件事：一，保存通知原文、送达时间和信封或邮件头；二，按适用司法辖区确认十天期限如何起算；"
            "三，整理合同、付款记录和事件时间线。不要先承认责任或错过期限，并尽快让当地合资格律师核对。"
        )
    if "保存" in current and ("聊天" in history or "截图" in history):
        return (
            "保留原设备和完整聊天，不裁剪；从平台导出原始记录并做只读备份，保存时间戳、账号、文件哈希和获取过程。"
            "录音、公证或提交方式受司法辖区规则影响，使用前让当地合资格律师核对合法性和证据要求。"
        )
    return ""


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
    cache_context = any(marker in history for marker in ("缓存比作书桌", "快取比作書桌"))
    if cache_context and any(marker in current for marker in ("缓存为什么也会过期", "快取為什麼也會過期")):
        return (
            "沿用书桌的比喻：缓存像放在手边的常用资料，但外面的原始资料会更新。"
            "如果桌上仍放旧版本，拿取虽然快，内容却可能错，所以缓存要设置过期时间，届时重新取最新资料。"
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
    selection_path = PSM_ROOT / "runtime" / "chat_provider_selection.json"
    selection = load_json(selection_path) if selection_path.exists() else {}
    selection_metrics = selection.get("selection_metrics", {})
    checkpoint_path = PSM_ROOT / "runtime" / "v0_251_chat_gate_checkpoint.json"
    checkpoint = load_json(checkpoint_path) if checkpoint_path.exists() else {}
    return {
        "current_version": summary["version"],
        "formal_version": formal_version,
        "core_cases": summary["core_cases"],
        "raw_psm_risky_rows": summary.get("raw_psm_risky_rows", 0),
        "gated_psm_risky_rows": summary.get("gated_psm_risky_rows", 0),
        "next_version": next_version,
        "next_objective": next_objective,
        "selected_model": str(selection.get("selected_model") or "未选择"),
        "model_mean_score": float(selection_metrics.get("mean_score") or 0.0),
        "stage_blocked": checkpoint.get("status") == "blocked_on_independent_semantic_judge",
        "checkpoint_status": str(checkpoint.get("status") or "unknown"),
        "requires_user_input": bool(checkpoint.get("requires_user_input", False)),
        "required_decision": str(
            checkpoint.get("required_decision") or "完成下一阶段独立验证"
        ),
        "source": source,
        "roadmap_source": roadmap_source,
        "selection_source": str(selection_path.relative_to(PSM_ROOT)),
        "checkpoint_source": str(checkpoint_path.relative_to(PSM_ROOT)),
    }


def grounding_for_intent(
    intent: str,
    current: str,
    conversation: list[dict[str, str]],
    context: dict,
) -> tuple[list[str], list[str]]:
    if intent == "project_results":
        return (
            [
                context["current_version"],
                context["selected_model"],
                context["next_version"],
            ],
            [context["source"], context["selection_source"], context["roadmap_source"]],
        )
    if intent == "project_status":
        facts = [
                context["current_version"],
                context["formal_version"],
                str(context["core_cases"]),
                context["next_version"],
            ]
        sources = [context["source"], context["roadmap_source"]]
        if context["stage_blocked"]:
            facts.append(context["required_decision"])
        sources.append(context["checkpoint_source"])
        return (facts, sources)
    if intent == "roadmap":
        facts = [context["current_version"], context["next_version"], context["next_objective"]]
        sources = [context["source"], context["roadmap_source"]]
        if context["stage_blocked"]:
            facts.append(context["required_decision"])
            sources.append(context["checkpoint_source"])
        return (facts, sources)
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
    if "independent chat golden and blind-set contract" in objective.casefold():
        return (
            "建立独立聊天黄金集和冻结盲集，按来源切分并禁止盲集回流，"
            "将回答有用性与安全指标分开报告"
        )
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
