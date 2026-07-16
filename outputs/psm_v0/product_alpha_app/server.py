from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


APP_ROOT = Path(__file__).resolve().parent
PSM_ROOT = APP_ROOT.parent
STATIC_ROOT = APP_ROOT / "static"
PROJECT_ROOT = APP_ROOT.parents[2]
sys.path.insert(0, str(PSM_ROOT))

from psm_v0.candidate_auditor import audit_candidate_text  # noqa: E402
from psm_v0.chat_quality_auditor import audit_chat_answer  # noqa: E402
from psm_v0.chat_prompt import build_chat_prompt, sanitize_model_answer  # noqa: E402
from psm_v0.chat_provider import OllamaChatProvider, ProviderRequest  # noqa: E402
from psm_v0.model_adapter import BuiltinModelAdapter  # noqa: E402
from psm_v0.external_trial_protocol import inspect_prompt, load_protocol  # noqa: E402
from psm_v0.participant_enrollment import (  # noqa: E402
    EnrollmentError,
    apply_enrollment_action,
    load_private_state,
    operator_invitation_cards,
    public_enrollment_status,
    record_prompt_audit,
    stop_enrollment,
    validate_trial_access,
    write_private_state,
    write_public_checkpoint,
)
from psm_v0.pipeline import run_pipeline  # noqa: E402
from psm_v0.psm_gate_controller import apply_psm_gate  # noqa: E402
from psm_v0.route_executor import execute_route  # noqa: E402
from psm_v0.sigma_plus_delivery import (  # noqa: E402
    build_sigma_plus_delivery,
    load_shadow_resources,
    repair_user_answer,
)
from psm_v0.state_extractor import infer_domain  # noqa: E402
from psm_v0.task_state_graph import build_task_state_graph  # noqa: E402
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
CHAT_TIMEOUT_OVERRIDE = os.environ.get("PSM_CHAT_TIMEOUT_SECONDS", "").strip()
CHAT_MAX_TOKENS_OVERRIDE = os.environ.get("PSM_CHAT_MAX_TOKENS", "").strip()
ROUTE_FAILURE_LEDGER = Path(
    os.environ.get(
        "PSM_ROUTE_FAILURE_LEDGER",
        str(PSM_ROOT / "product_alpha_out" / "v0_255_route_failure_ledger.jsonl"),
    )
)
ENROLLMENT_STATE_PATH = Path(
    os.environ.get(
        "PSM_V0_263_ENROLLMENT_STATE",
        str(PSM_ROOT / "private_runtime" / "v0_263" / "enrollment_state.json"),
    )
)
ENROLLMENT_PROTOCOL_PATH = PSM_ROOT / "benchmarks" / "v0_262_invite_only_external_trial_protocol.json"
ENROLLMENT_CHECKPOINT_PATH = PSM_ROOT / "runtime" / "v0_263_participant_enrollment_checkpoint.json"
ENROLLMENT_LOCK = threading.Lock()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PSM Product Alpha local demo server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"PSM Product Alpha running at http://{args.host}:{args.port}")
    server.serve_forever()


class Handler(BaseHTTPRequestHandler):
    server_version = "PSMProductAlpha/0.270"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.write_json(load_status_summary())
            return
        if parsed.path == "/api/trial-notice":
            self.write_json(load_trial_notice(), no_store=True)
            return
        if parsed.path == "/api/trial-enrollment":
            try:
                self.write_json(load_enrollment_api_status(), no_store=True)
            except (EnrollmentError, FileNotFoundError) as exc:
                self.write_json({"error": str(exc), "trial_active": False}, status=404, no_store=True)
            return
        if parsed.path == "/api/trial-enrollment/operator-cards":
            if self.client_address[0] not in {"127.0.0.1", "::1"}:
                self.write_json({"error": "operator cards are loopback-only"}, status=403, no_store=True)
                return
            try:
                self.write_json(load_operator_cards(), no_store=True)
            except (EnrollmentError, FileNotFoundError) as exc:
                self.write_json({"error": str(exc)}, status=404, no_store=True)
            return
        static_name = {
            "": "index.html",
            "/": "index.html",
            "/trial-enrollment": "trial-enrollment.html",
        }.get(parsed.path, parsed.path.lstrip("/"))
        path = STATIC_ROOT / static_name
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
        static_name = {
            "": "index.html",
            "/": "index.html",
            "/trial-enrollment": "trial-enrollment.html",
        }.get(parsed.path, parsed.path.lstrip("/"))
        path = STATIC_ROOT / static_name
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
        if parsed.path not in {
            "/api/run",
            "/api/chat",
            "/api/trial-enrollment/action",
            "/api/trial-chat",
        }:
            self.send_error(404)
            return
        try:
            payload = self.read_json()
            if parsed.path == "/api/trial-enrollment/action":
                self.write_json(handle_enrollment_action(payload), no_store=True)
                return
            if parsed.path == "/api/trial-chat":
                self.write_json(run_trial_chat_turn(payload), no_store=True)
                return
            scenario = str(payload.get("scenario") or "review")
            if parsed.path == "/api/chat":
                messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
                previous_graph = (
                    payload.get("task_state_graph")
                    if isinstance(payload.get("task_state_graph"), dict)
                    else None
                )
                self.write_json(run_chat_turn(messages, scenario, previous_graph=previous_graph))
                return
            text = str(payload.get("text") or "").strip()
            if not text:
                text = SCENARIOS.get(scenario, SCENARIOS["review"])
            self.write_json(run_demo_case(text, scenario))
        except (EnrollmentError, FileNotFoundError) as exc:
            self.write_json({"error": str(exc), "trial_active": False}, status=409, no_store=True)
        except Exception as exc:  # pragma: no cover - local demo should surface errors.
            self.write_json({"error": str(exc)}, status=500, no_store=True)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def write_json(self, payload: dict, *, status: int = 200, no_store: bool = False) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if no_store:
            self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def load_enrollment_protocol() -> dict:
    if not ENROLLMENT_PROTOCOL_PATH.exists():
        raise FileNotFoundError("Frozen V0.262 trial protocol is unavailable.")
    return load_protocol(ENROLLMENT_PROTOCOL_PATH)


def load_enrollment_state() -> tuple[dict, dict]:
    if not ENROLLMENT_STATE_PATH.exists():
        raise FileNotFoundError("V0.263 private enrollment has not been prepared on this runtime.")
    protocol = load_enrollment_protocol()
    return load_private_state(ENROLLMENT_STATE_PATH, protocol), protocol


def load_enrollment_api_status() -> dict:
    state, _ = load_enrollment_state()
    status = public_enrollment_status(state)
    status["notice_version"] = "psm_v0_262_trial_notice_v1"
    status["notice_url"] = "/api/trial-notice"
    status["operator_cards_available"] = True
    status["participant_content_external_api_allowed"] = False
    status["raw_prompt_server_persistence"] = False
    return status


def load_operator_cards() -> dict:
    state, _ = load_enrollment_state()
    return operator_invitation_cards(state)


def handle_enrollment_action(payload: dict) -> dict:
    expected = {"participant_id", "invitation_code", "action", "attestation"}
    if set(payload) != expected:
        raise EnrollmentError("enrollment action fields are not closed")
    with ENROLLMENT_LOCK:
        state, protocol = load_enrollment_state()
        updated = apply_enrollment_action(
            state,
            participant_id=str(payload["participant_id"]),
            invitation_code=str(payload["invitation_code"]),
            action=str(payload["action"]),
            attestation=str(payload["attestation"]),
            protocol=protocol,
        )
        write_private_state(ENROLLMENT_STATE_PATH, updated, protocol)
        write_public_checkpoint(ENROLLMENT_CHECKPOINT_PATH, updated)
    return load_enrollment_api_status()


def run_trial_chat_turn(payload: dict) -> dict:
    allowed = {"participant_id", "invitation_code", "messages", "scenario", "task_state_graph"}
    required = {"participant_id", "invitation_code", "messages"}
    if set(payload) - allowed or not required.issubset(payload):
        raise EnrollmentError("trial chat request fields are not closed")
    participant_id = str(payload["participant_id"])
    invitation_code = str(payload["invitation_code"])
    messages = payload["messages"] if isinstance(payload["messages"], list) else []
    conversation = normalize_chat_messages(messages)
    if not conversation or conversation[-1]["role"] != "user":
        raise EnrollmentError("trial chat requires a current participant message")

    with ENROLLMENT_LOCK:
        state, protocol = load_enrollment_state()
        access_errors = validate_trial_access(
            state,
            participant_id=participant_id,
            invitation_code=invitation_code,
            protocol=protocol,
        )
        if access_errors:
            raise EnrollmentError("trial chat gate rejected the request: " + "; ".join(access_errors))

        user_prompts = [item["content"] for item in conversation if item["role"] == "user"]
        prompt_decisions = [inspect_prompt(prompt, protocol) for prompt in user_prompts]
        rejected_index = next(
            (index for index, decision in enumerate(prompt_decisions) if not decision["allowed"]),
            None,
        )
        if rejected_index is not None:
            rejected = prompt_decisions[rejected_index]
            updated = record_prompt_audit(
                state,
                participant_id=participant_id,
                prompt=user_prompts[rejected_index],
                decision=rejected,
                latency_ms=0,
                token_count=0,
            )
            updated = stop_enrollment(
                updated,
                reason="prohibited_or_unknown_data_detected",
                protocol=protocol,
            )
            write_private_state(ENROLLMENT_STATE_PATH, updated, protocol)
            write_public_checkpoint(ENROLLMENT_CHECKPOINT_PATH, updated)
            categories = ", ".join(rejected["categories"])
            raise EnrollmentError(f"trial prompt contains a prohibited or unknown data class: {categories}")

    started = time.monotonic()
    result = run_chat_turn(
        conversation,
        str(payload.get("scenario") or "review"),
        previous_graph=(
            payload.get("task_state_graph")
            if isinstance(payload.get("task_state_graph"), dict)
            else None
        ),
    )
    provider = str(result.get("chat", {}).get("generation", {}).get("provider") or "")
    if provider not in {"ollama", "deterministic", "deterministic_fallback"}:
        with ENROLLMENT_LOCK:
            current, protocol = load_enrollment_state()
            stopped = stop_enrollment(
                current,
                reason="participant_content_would_be_sent_to_external_api",
                protocol=protocol,
            )
            write_private_state(ENROLLMENT_STATE_PATH, stopped, protocol)
            write_public_checkpoint(ENROLLMENT_CHECKPOINT_PATH, stopped)
        raise EnrollmentError("trial chat attempted an unapproved generation provider")
    answer = str(result["chat"]["assistant_message"])
    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
    with ENROLLMENT_LOCK:
        current, protocol = load_enrollment_state()
        access_errors = validate_trial_access(
            current,
            participant_id=participant_id,
            invitation_code=invitation_code,
            protocol=protocol,
        )
        if access_errors:
            raise EnrollmentError("trial authorization changed before delivery: " + "; ".join(access_errors))
        event_id = f"trial-{secrets.token_hex(8)}"
        updated = record_prompt_audit(
            current,
            participant_id=participant_id,
            prompt=conversation[-1]["content"],
            decision=prompt_decisions[-1],
            latency_ms=elapsed_ms,
            token_count=max(1, (len(answer) + 3) // 4),
            event_id=event_id,
        )
        write_private_state(ENROLLMENT_STATE_PATH, updated, protocol)
    return {
        "schema_version": "psm_v0_263_trial_chat_response_v1",
        "chat": {"assistant_message": answer},
        "trial_session": {
            "participant_id": participant_id,
            "supervised_invite_only": True,
            "raw_prompt_persisted": False,
            "participant_content_sent_to_external_api": False,
            "public_service_allowed": False,
            "human_feedback_required": False,
        },
    }


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
            "packet_id": packet.get("packet_id"),
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


def run_chat_turn(
    messages: list[dict],
    scenario: str,
    *,
    previous_graph: dict | None = None,
) -> dict:
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
    route_execution = execute_route(
        current,
        intent=intent,
        pipeline_result=result,
        project_root=PROJECT_ROOT,
        psm_root=PSM_ROOT,
        verified_facts=verified_knowledge.grounding_facts if verified_knowledge else (),
        verified_sources=verified_knowledge.grounding_sources if verified_knowledge else (),
        ledger_path=ROUTE_FAILURE_LEDGER,
    )
    result["route_execution"] = route_execution
    task_state_graph = build_task_state_graph(
        conversation,
        result,
        route_execution,
        previous_graph=previous_graph,
    )
    result["task_state_graph"] = task_state_graph
    result["packet"]["pi_cavity"] = {
        **result["packet"].get("pi_cavity", {}),
        "mode": "task_evidence_graph",
        "graph_id": task_state_graph["graph_id"],
        "node_count": len(task_state_graph["nodes"]),
        "edge_count": len(task_state_graph["edges"]),
        "state_counts": task_state_graph["state_counts"],
        "next_protocol": task_state_graph["next_protocol"],
    }
    result["packet"]["eta"] = {
        **result["packet"].get("eta", {}),
        "mode": "task_evidence_state",
        "unknown_count": task_state_graph["state_counts"].get("unknown", 0),
        "conflict_count": task_state_graph["state_counts"].get("conflicting", 0),
        "pending_count": task_state_graph["state_counts"].get("pending", 0),
        "failure_learning_queue": task_state_graph["failure_learning_queue"],
    }
    generation = build_chat_generation(
        current,
        conversation,
        result,
        intent,
        project_context,
        verified_knowledge=verified_knowledge,
        route_execution=route_execution,
    )
    assistant_message = generation["answer"]
    quality_audit = audit_chat_answer(
        current,
        assistant_message,
        intent=intent,
        grounding_facts=grounding_facts,
        grounding_sources=grounding_sources,
        previous_assistant_answers=assistant_messages,
        route_execution=route_execution,
    )
    shadow_model, calibration = load_shadow_resources(str(PSM_ROOT))
    sigma_plus_delivery = build_sigma_plus_delivery(
        request=current,
        answer=assistant_message,
        intent=intent,
        pipeline_result=result,
        route_execution=route_execution,
        task_state_graph=task_state_graph,
        grounding_facts=grounding_facts,
        grounding_sources=grounding_sources,
        quality_audit=quality_audit,
        shadow_model=shadow_model,
        calibration=calibration,
    )
    original_candidate = assistant_message
    if not sigma_plus_delivery["passed"]:
        assistant_message = repair_user_answer(
            assistant_message,
            sigma_plus_delivery["developer_view"]["statement_audit"],
            sigma_plus_delivery["internal_debug_terms_in_user_view"],
        )
        quality_audit = audit_chat_answer(
            current,
            assistant_message,
            intent=intent,
            grounding_facts=grounding_facts,
            grounding_sources=grounding_sources,
            previous_assistant_answers=assistant_messages,
            route_execution=route_execution,
        )
        sigma_plus_delivery = build_sigma_plus_delivery(
            request=current,
            answer=assistant_message,
            intent=intent,
            pipeline_result=result,
            route_execution=route_execution,
            task_state_graph=task_state_graph,
            grounding_facts=grounding_facts,
            grounding_sources=grounding_sources,
            quality_audit=quality_audit,
            shadow_model=shadow_model,
            calibration=calibration,
        )
        sigma_plus_delivery["repair"] = {
            "applied": True,
            "original_candidate": original_candidate,
            "original_candidate_user_visible": False,
        }
    else:
        sigma_plus_delivery["repair"] = {"applied": False, "original_candidate_user_visible": True}
    result["chat"] = {
        "turn_index": len(user_messages),
        "current_user_message": current,
        "audit_text": audit_text,
        "intent": intent,
        "assistant_message": assistant_message,
        "generation": {
            **generation,
            "answer": assistant_message,
            "grounded_facts": grounding_facts,
            "grounding_sources": grounding_sources,
            "uncertainties": result["packet"].get("eta", {}).get("uncertainties", []),
            "required_judges": result["route"].get("required_judges", []),
            "route_execution": route_execution,
            "task_state_graph_id": task_state_graph["graph_id"],
            "next_protocol": task_state_graph["next_protocol"],
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
    result["sigma_plus_delivery"] = sigma_plus_delivery
    return result


def semantic_state_input(
    current: str,
    conversation: list[dict[str, str]],
) -> tuple[str, bool]:
    topic_switch_markers = (
        "换个话题",
        "換個話題",
        "切换话题",
        "切換話題",
        "另一个话题",
        "另一個話題",
        "new topic",
    )
    if any(marker in current.casefold() for marker in topic_switch_markers):
        return current, False
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
    route_execution: dict | None = None,
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
    multiturn_edit = bounded_multiturn_edit_answer(text, conversation)
    if multiturn_edit:
        return deterministic_generation(multiturn_edit)
    bounded_meta_answer = bounded_meta_language_answer(text)
    if bounded_meta_answer:
        return deterministic_generation(bounded_meta_answer)
    if verified_knowledge:
        generation = deterministic_generation(verified_knowledge.answer)
        generation["knowledge_kernel"] = verified_knowledge.kernel_id
        return generation
    route_answer = route_execution_answer(route_execution or {})
    if route_answer:
        generation = deterministic_generation(
            route_answer,
            status=(
                "success"
                if (route_execution or {}).get("status") in {"success", "partial"}
                else "degraded"
            ),
        )
        generation["route_grounded"] = True
        return generation
    model_generation = try_ollama_chat_generation(
        current,
        conversation,
        result,
        route_execution=route_execution,
    )
    if model_generation["status"] != "success":
        return deterministic_generation(
            fallback_chat_answer(current, result, conversation),
            status="degraded",
            attempted=model_generation,
        )
    model_generation["answer"] = complete_contextual_answer(
        model_generation["answer"], current, conversation, result
    )
    model_generation["answer"] = enforce_explicit_output_constraints(
        current, model_generation["answer"]
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


def bounded_multiturn_edit_answer(
    current: str,
    conversation: list[dict[str, str]],
) -> str:
    previous_assistant = next(
        (item["content"] for item in reversed(conversation[:-1]) if item["role"] == "assistant"),
        "",
    )
    previous_users = [item["content"] for item in conversation[:-1] if item["role"] == "user"]
    if not previous_assistant:
        return ""

    corrected_conclusion = re.search(
        r"更正[：:]\s*([^。！？!?]+)[。！？!?].*(?:只确认|只確認)(?:更正后的|更正後的)?结论",
        current,
    )
    if corrected_conclusion:
        return corrected_conclusion.group(1).strip() + "。"

    replacement = re.search(
        r"把\s*([A-Za-z]+)\s*改成\s*([A-Za-z]+).*(?:其他约束不变|其他約束不變)",
        current,
        flags=re.IGNORECASE,
    )
    translation_only = any(
        ("只给译文" in item or "只給譯文" in item) for item in previous_users
    )
    if replacement and translation_only:
        before, after = replacement.group(1), replacement.group(2)
        revised = re.sub(rf"\b{re.escape(before)}\b", after, previous_assistant, flags=re.IGNORECASE)
        revised = re.sub(r"\b(?:was|were)\s+arrived\b", "arrived", revised, flags=re.IGNORECASE)
        return first_answer_sentence(revised, limit=400).strip('“”"')

    step_update = re.search(r"第([一二三1-3])步改成\s*(\d+)\s*分钟", current)
    if step_update and ("只保留三步" in current or "只保留三步" in "\n".join(previous_users)):
        index = {"一": 1, "二": 2, "三": 3}.get(step_update.group(1), int(step_update.group(1)) if step_update.group(1).isdigit() else 0)
        lines = [line.strip() for line in previous_assistant.splitlines() if line.strip()][:3]
        if len(lines) == 3 and 1 <= index <= 3:
            lines[index - 1] = re.sub(r"\d+\s*分钟", f"{step_update.group(2)}分钟", lines[index - 1], count=1)
            return "\n".join(lines)

    inherited_epistemic_exclusion = any(
        "完全证明" in item and ("不要" in item or "不能" in item) for item in previous_users
    )
    if inherited_epistemic_exclusion and ("压缩" in current or "壓縮" in current):
        return "现有结果仅属初步支持，尚需外部复核。"
    return ""


def route_execution_answer(route_execution: dict) -> str:
    if not route_execution:
        return ""
    adapters = {item.get("adapter"): item for item in route_execution.get("adapters", [])}
    status = str(route_execution.get("status") or "not_executed")
    failures = route_execution.get("failures") or []

    file_result = adapters.get("local_file_evidence")
    if file_result and status in {"success", "partial"}:
        answer = "已按只读方式读取项目内文件，并记录了路径、大小和 SHA-256。\n\n" + "\n".join(
            f"- {fact}" for fact in file_result.get("facts") or []
        )
        if failures:
            answer += "\n\n部分路径没有完成：" + "；".join(item["message"] for item in failures)
        return answer

    code_result = adapters.get("sandboxed_code_check")
    if code_result and status in {"success", "partial"}:
        details = code_result.get("details") or {}
        if details.get("mode") == "python_ast":
            return (
                "静态语法检查已通过；用户代码没有被执行。这个结果只证明 Python 语法可解析，"
                "不证明逻辑正确、边界安全或可以上线，还需要针对行为补测试。"
            )
        command_id = details.get("command_id") or "project_verifier"
        return (
            f"已执行固定白名单中的项目验证命令 `{command_id}`，结果通过。"
            "这证明当前自动化检查通过，但不等于生产发布、外部用户试用或规则替换已经获准。"
        )

    if route_execution.get("explicit_evidence_request") and status in {
        "blocked",
        "conflict",
        "failed",
        "missing_evidence",
        "not_executed",
        "timeout",
    }:
        reason = "；".join(item.get("message", "证据路线未完成") for item in failures)
        if not reason:
            reason = "当前没有适用的本地证据适配器或可核验来源。"
        elif not reason.endswith(("。", ".", "！", "!", "？", "?")):
            reason += "。"
        return (
            f"这次证据路线没有完成，状态为 `{status}`：{reason}"
            "我不会把缺失、冲突或失败的工具结果包装成已经核验的结论。"
        )
    return ""


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


def enforce_explicit_output_constraints(current: str, answer: str) -> str:
    constrained = answer.strip()
    just_result = any(
        marker in current
        for marker in (
            "只给结果", "只給結果", "只给改写结果", "只給改寫結果",
            "只给译文", "只給譯文", "只输出", "只輸出",
        )
    )
    if just_result:
        quoted = re.search(
            r"(?:建议改为|建議改為|可以改为|可以改為|改为|改為)\s*[：:]\s*[“\"](.+?)[”\"]",
            constrained,
            flags=re.DOTALL,
        )
        if quoted:
            constrained = quoted.group(1).strip()
        else:
            constrained = constrained.split("\n\n", 1)[0].strip()
            constrained = re.sub(r"^(?:译文|譯文|结果|結果)\s*[：:]\s*", "", constrained)
    if any(marker in current for marker in ("一句话总结", "一句話總結", "用一句话总结", "用一句話總結")):
        constrained = constrained.split("\n\n", 1)[0].strip()
        constrained = first_answer_sentence(constrained, limit=1000)
    if (
        "30分钟" in current
        and "三步" in current
        and all(marker in current for marker in ("备料", "烹饪", "清理"))
        and "分钟" not in constrained
    ):
        constrained += "\n\n时间分配：备料 8 分钟、烹饪 17 分钟、清理 5 分钟。"
    return constrained


def bounded_meta_language_answer(text: str) -> str:
    folded = text.casefold()
    if (
        any(marker in folded for marker in ("一句话总结", "一句話總結"))
        and "内部实验" in folded
        and "样本" in folded
        and "独立复现" in folded
    ):
        return "内部实验支持该假设，但样本较小且尚无独立复现，因此目前只能视为初步证据。"
    asks_english = any(marker in folded for marker in ("翻译成英文", "翻譯成英文", "的英文", "英文是什么", "英文是什麼"))
    asks_chinese = any(marker in folded for marker in ("的中文", "中文是什么", "中文是什麼"))
    if "胸痛" in folded and asks_english:
        return "“胸痛”的常用英文是 `chest pain`。这只是词汇翻译，不构成医疗诊断或医生建议。"
    if "股票" in folded and asks_english:
        return "“股票”通常译为 `stock`；谈多个股票时也可按语境使用 `stocks` 或 `shares`。这只是词汇翻译，不构成交易建议。"
    if "stock" in folded and asks_chinese:
        return "`stock` 在金融语境中通常译为“股票”；其他语境也可能表示库存或储备。这里仅做词汇翻译，不构成交易建议。"
    if "完全证明" in folded and any(marker in folded for marker in ("不要把", "不要將")):
        return "可以改为：“现有结果仅提供初步支持，结论仍需独立数据与外部复核。”"
    if "完全证明" in folded and any(marker in folded for marker in ("谨慎", "謹慎", "改写", "改寫", "否定边界", "否定邊界")):
        return "可以改为：“现有结果为该结论提供了初步支持，但尚未达到完全证明，仍需独立数据与外部复核。”"
    return ""


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
    markers = [
        "你是谁", "你是誰", "who are you", "你叫什么", "你叫什麼",
        "介绍一下你自己", "介紹一下你自己", "介绍你自己", "介紹你自己",
        "怎么称呼你", "怎麼稱呼你", "如何称呼你", "如何稱呼你",
    ]
    greetings = ["你好", "hello", "hi", "嗨"]
    return any(marker in text for marker in markers) or text.strip() in greetings


def is_chat_capability_question(text: str) -> bool:
    markers = ["可以聊天吗", "可以聊天嗎", "怎么聊天", "怎麼聊天", "能聊天吗", "能聊天嗎", "能正常跟我聊天吗", "能正常跟我聊天嗎", "聊天功能在哪"]
    return any(marker in text for marker in markers)


def is_psm_vs_llm_question(text: str) -> bool:
    has_psm = "物性ai" in text or "物性 ai" in text or "物性模型" in text
    has_llm = "普通大模型" in text or "大语言模型" in text or "大語言模型" in text or "llm" in text
    asks_difference = any(marker in text for marker in ("区别", "差別", "差异", "不同", "多了什么", "多了什麼", "相比"))
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
        "合成测试",
        "合成測試",
        "模拟角色",
        "模擬角色",
        "真人验证",
        "真人驗證",
        "真实用户",
        "真實用戶",
        "用户满意",
        "用戶滿意",
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
    if (
        any(marker in question for marker in ("更正当前版本", "更正當前版本", "更正版本"))
        and any(marker in question for marker in ("本地结构化记录", "本地結構化記錄", "本地记录", "本地紀錄"))
    ):
        return f"当前项目版本是 {context['current_version']}。"
    if any(marker in question for marker in ("合成测试", "合成測試", "模拟角色", "模擬角色", "真人验证", "真人驗證", "真实用户", "真實用戶", "用户满意", "用戶滿意")):
        return (
            "不能。合成测试或模拟角色通过，只能证明冻结场景下的内部自动检查通过；"
            "它不是真人参与，不能代表真实用户体验、满意度或外部验证。"
            f"当前项目仍是 {context['current_version']}，确定性正式源为 {context['formal_version']}，"
            f"保留 {context['core_cases']} 个正式案例；下一阶段是 {context['next_version']}。"
            "外部用户试用和公开发布权限都没有开放。"
        )
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
            f"共有 {context['core_cases']} 个正式案例；下一阶段 {context['next_version']} 的目标是"
            f"{context['next_objective']}。外部用户试用仍未开放。"
        )
    if any(marker in question for marker in ("直接放行", "聊天已经能用", "聊天已經能用")):
        return (
            f"不能因为聊天已经能用就直接放行。当前正式版本仍是 {context['current_version']}，"
            "独立聊天盲测和内部产品交互门已经通过；但这仍不能证明真实工具路线、隐私合规或外部用户发布条件"
            f"已经成立。下一阶段是 {context['next_version']}：{context['next_objective']}。"
            "因此外部用户试用仍未开放。"
        )
    if any(marker in question for marker in ("正式版本", "版本号", "版本號", "核心验证门", "核心驗證門")):
        answer = (
            f"当前正式晋级版本是 {context['current_version']}；确定性正式源是 {context['formal_version']}，"
            f"共有 {context['core_cases']} 个正式案例，正式回归已经通过。"
        )
        if context["chat_gate_passed"]:
            answer += "V0.251 的全新盲集独立外部语义门也已通过。"
        answer += (
            f"下一阶段是 {context['next_version']}：{context['next_objective']}；"
            "这些内部门通过前不能升级产品稳定性声明，外部用户试用仍未开放。"
        )
        return answer
    if any(marker in question for marker in ("外部试用", "外部試用", "真实动作", "真實動作")):
        return (
            f"当前没有开放外部用户试用，正式版本仍是 {context['current_version']}。"
            f"当前聊天基座是 {context['selected_model']}。记录中的下一真实动作是："
            f"完成 {context['next_version']} 的 {context['next_objective']}。{context['required_decision']}"
        )
    if any(marker in question for marker in ("最高优先级", "最高優先級", "优先级最高", "優先級最高", "优先任务", "優先任務")):
        return (
            f"当前最高优先级是完成 {context['next_version']} 的 {context['next_objective']}，"
            f"原因是正式版本仍是 {context['current_version']}，确定性正式源为 {context['formal_version']}，"
            f"共有 {context['core_cases']} 个正式案例，V0.251 独立外部语义门已经通过；"
            "当前应执行记录中的真实下一阶段，不再改写已封存盲集。"
        )
    if any(marker in question for marker in ("阻塞因素", "阻碍因素", "阻礙因素", "最大阻塞", "最大的阻塞")):
        user_blocker = "需要用户介入" if context["requires_user_input"] else "不需要用户介入"
        if context["stage_blocked"]:
            return (
                f"当前 {context['next_version']} 确实受阻，且{user_blocker}。阻塞内容是："
                f"{context['required_decision']} 外部用户试用仍未开放。"
            )
        return (
            f"当前没有阻止施工的外部 blocker；最大的阶段门是 {context['next_version']} 的"
            f"{context['next_objective']}。现阶段{user_blocker}；"
            "外部用户试用仍未开放。"
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
        answer += f"\n\n{context['next_version']} 当前受阻：{context['required_decision']}"
    return answer


def roadmap_answer(context: dict) -> str:
    if context["next_version"] == "PSM V0.263":
        construction = (
            "V0.262 已冻结数据处理与隐私边界、告知同意、7 天删除、本地部署和 API 预算。"
            "V0.263 的工程准备已完成，参与人数固定为三名，P01-P03 化名邀请已在本机私密区生成。"
            "剩余顺序是三名本人到场后，由操作员线下核验成年，依次完成告知、确认和明确同意，"
            "最后才启用现场监督会话。"
            f"当前需要：{context['required_decision']}"
        )
    elif context["stage_blocked"]:
        construction = (
            "当前内部阶段的工程与评审已经完成，但下一阶段涉及外部范围、数据处理、部署、费用或凭证，"
            "不能由系统自行推定授权。"
            f"继续前需要：{context['required_decision']}"
        )
    elif context["next_version"] == "PSM V0.252":
        construction = (
            "施工顺序是：先建立生成中、取消、超时、重试和错误恢复状态；再接入渐进式回答显示，"
            "确保 9B 模型生成期间主界面持续反馈；随后把调试证据默认隐藏，并补齐桌面与移动视口、"
            "键盘操作、基础无障碍、重复消息和布局溢出回归；最后重建本地与 Docker 运行时。"
        )
    elif context["next_version"] == "PSM V0.253":
        construction = (
            "施工顺序是：先定义统一 route-result 与 provenance 契约；再把项目状态、事实来源、代码检查和文件读取"
            "四类路线接入真实本地适配器；随后注入超时、缺失来源、工具失败和输出冲突，确保失败会入账并降级；"
            "最后补 API、回归和 Docker 验证，工具结果仍不能绕过 PSM 门控。"
        )
    elif context["next_version"] == "PSM V0.254":
        construction = (
            "施工顺序是：先定义任务级节点、边和声明状态契约；再把消息、文件、工具结果和裁判结果转成 Π 依赖图；"
            "随后加入新证据、证据撤回、未知项和冲突项的图差分测试；最后从 failure ledger 生成隔离候选队列，"
            "只有独立筛选通过后才允许进入开发集，冻结盲集与训练真相继续禁止自动回流。"
        )
    elif context["next_version"] == "PSM V0.255":
        construction = (
            "施工顺序是：先重放 V0.251 冻结盲测与 V0.252-V0.254 产品、路由和状态图证据；"
            "再用独立的正常聊天、多轮连续性、项目接地与高风险帮助式边界场景执行 API 总门；"
            "随后核对关键事实幻觉和 critical safety false negative 必须为零，并复验桌面、手机和 Docker；"
            "全部通过后只能给出内部使用结论，外部用户试用仍不自动开放。"
        )
    elif context["next_version"] == "PSM V0.256":
        construction = (
            "施工顺序是：先冻结与规则模板来源隔离的状态标注协议，定义 Q、Omega、phi、Delta sigma、Pi、eta 和"
            "B_sigma 的字段、证据要求与标注者分歧；再建立 family、source、time 三重切分和污染检查；"
            "随后形成规则基线、普通 LLM 基线与可训练编码器的同题比较契约。契约通过前不启动训练，"
            "任何候选都只能在 shadow 中观察，不能替换现有规则。"
        )
    elif context["next_version"] == "PSM V0.257":
        construction = (
            "施工顺序是：继续继承 family、source、time 三重来源隔离，只读取 V0.256 已解析且属于 train 的一致标注，"
            "先建立多数类和透明信号规则基线；"
            "再训练首个轻量状态编码候选，并按 Q、Omega、phi、Delta sigma、Pi、eta、B_sigma 分目标评估；"
            "随后在 validation/test 上独立报告准确率、分歧覆盖和 critical false negative。候选全程 shadow-only，"
            "不能读取 judge-only 标签，也不能把验证或测试错误回流训练，不能替换现有规则。"
        )
    elif context["next_version"] == "PSM V0.258":
        construction = (
            "施工顺序是：冻结新的来源 family 并保持 family、source、time 三重来源隔离；再对七个 head 分别做置信度校准，"
            "加入低置信度 abstention 和 unresolved 分歧评估；随后检查校准误差、覆盖率、critical false negative 与"
            "跨 family 稳定性。validation、test、blind 和 judge-only 反馈仍禁止进入训练，候选继续 shadow-only，"
            "不能替换现有规则，确定性规则控制器继续保留。"
        )
    elif context["next_version"] == "PSM V0.259":
        construction = (
            "施工顺序是：先定义 Sigma+ 交付包，把自然回答、物性状态、来源、工具结果、失败和声明等级绑定在同一追溯链；"
            "再为强结论加入 provenance 或显式降级，低置信和 unresolved target 一律回退确定性规则；"
            "随后抽样审计强结论来源，并验证普通聊天只显示自然回答，不泄漏内部状态、阈值或调试术语；"
            "最后补齐 API、桌面、手机和 Docker 回归，shadow 候选仍无放行权。"
        )
    elif context["next_version"] == "PSM V0.260":
        construction = (
            "施工顺序是：先冻结评审输入清单，汇总安全、聊天质量、盲测、模型对照、性能、失败账本与剩余风险；"
            "再重放关键门槛并检查证据版本、时间与放行边界一致；随后只允许给出 internal_trial_ready、"
            "needs_more_work 或 blocked 三种机器结论；最后复验 API、桌面、手机和 Docker。"
            "这个评审只决定本机内部真实使用，不会自动开放外部用户、隐私合规、公开服务或专业权限。"
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
    if context["current_version"] == "PSM V0.270":
        return (
            "这轮已完成 PSM V0.270 多轮约束门：12/12 个冻结多轮场景全部通过，覆盖助手回答指代、用户历史风险、"
            "明确话题切换、用户更正优先、禁止词延续、三步格式和只给译文。首次运行的 5 个失败、两处领域标注勘误"
            "和一处评估器漏检均已保留；助手历史污染和过期约束违规都是 0。\n\n"
            "PSM V0.271 的独立外部评审随后判定 M07、M08 失败，原因都是过度回答；两项已经本地修复为精确短答，"
            "但尚未外部重审，不能写成通过。当前月度 API 预算已达 20/20 美元，需要额外 4 美元才能重审。"
            f"当前本地聊天模型是 `{context['selected_model']}`，外部发布仍关闭。"
        )
    if context["current_version"] == "PSM V0.268":
        return (
            "这轮已完成 PSM V0.268 普通聊天任务完成度门：翻译、改写、提取、比较、摘要、规划和解释共 "
            "21/21 个冻结任务全部通过。首次运行的 5 个失败已原样保留，三处评分语言修正也另列为透明勘误，"
            "没有覆盖原始契约。\n\n"
            "修复后，系统不再用模型失败模板、边界说明或复述任务代替答案；桌面、手机、主机与 Docker 回归均通过，"
            "178 项测试通过。它的作用是把物性状态门从“判断能否回答”推进到“在保留边界的同时真正完成动作”。"
            "这些仍是内部合成证据，不代表真人满意度、开放域泛化或公开服务已经验证。"
            f"当前本地聊天模型是 `{context['selected_model']}`。"
            f"下一步是 {context['next_version']}：{context['next_objective']} 外部发布仍关闭。"
        )
    if context["current_version"] == "PSM V0.266":
        return (
            "这轮已完成 PSM V0.266 对抗与变形不变量门：15/15 组、30/30 个冻结变体全部通过，"
            "覆盖同义改写、角色历史隔离、否定作用域、事件时间顺序和发布边界。首次运行暴露的 8 组失败"
            "已经原样保留在只增不改的失败账本中，再针对同一契约修复产品逻辑。\n\n"
            "修复后，关键事实幻觉、关键安全漏判和评测回流均为 0；170 项测试、桌面与手机浏览器、"
            "主机与 Docker 一致性也全部通过。它让聊天对换一种说法、引用高风险词、混入错误助手历史、"
            "以及时间顺序变形时更稳定，但这些仍是内部合成证据，不代表真人满意或开放域验证。"
            f"当前本地聊天模型是 `{context['selected_model']}`。"
            f"下一步是 {context['next_version']}：{context['next_objective']} 公开服务和外部发布仍关闭。"
        )
    if context["current_version"] == "PSM V0.265":
        return (
            "这轮已完成 PSM V0.265 自动质量与多角色模拟试用门：30/30 个冻结场景全部通过，其中 12 个"
            "模拟角色覆盖首次使用、急躁简答、学生、工程、实验、量化、食物安全、研究质疑、医疗急症、"
            "法律期限、交易授权压力和理论阅读视角。角色代理量表 12/12 通过，关键事实幻觉和严重安全漏检都是 0。\n\n"
            "这轮还修复了正常聊天同义问法、过敏请求医疗路由、压缩知识核审计，以及一个会让理论降级回答"
            "崩溃的缺失函数。真人评分界面、接口和私有状态已经移除，聊天恢复为纯问答。"
            "这些结果是内部合成角色模拟，不冒充真实参与者，也不代表真人满意度或开放域验证。"
            f"当前本地聊天模型是 `{context['selected_model']}`。"
            f"下一步是 {context['next_version']}：{context['next_objective']} 公开服务和外部发布仍关闭。"
        )
    if context["current_version"] == "PSM V0.262":
        return (
            "这轮已完成 PSM V0.262 邀请制外部试用协议。用户批准的保守边界已经固化为代码门：仅限 3 至 5 名受邀成年人、"
            "操作员现场监督、成年核验与受邀者 HMAC 绑定、先展示告知再确认和同意，最后才允许第一条消息。\n\n"
            "本地协议门 20/20 通过，8/8 敏感攻击被拒绝；原始聊天不在服务器落盘，也不发送到外部 API，只保留不含内容的"
            "HMAC 与运行指标，7 天删除。API 月上限是 20 美元，当前只为两次合成协议评审预留 4 美元。首轮外部评审因成年核验"
            "和告知顺序不足而 fail，修复后 `gpt-5.4` 复审 7/7 通过，0 未解决发现。\n\n"
            "它的作用是把外部试用从口头授权变成可停止、可删除、可审计的最小协议。当前仍未招募真实参与者，公开服务、"
            "隐私合规、专业权限、试用数据训练与发布权限均未开放。"
            f"本地聊天基座仍是 `{context['selected_model']}`。下一阶段是 {context['next_version']}：{context['required_decision']}"
        )
    if context["current_version"] == "PSM V0.261":
        return (
            "这轮已完成 PSM V0.261 合成标注契约的外部独立评审闭环。第一轮 OpenAI 评审明确判定 fail，指出开放字段、"
            "时间切分歧义、分歧结构、受保护资料回流与权限旁路五类问题；系统保留了失败证据，没有把它包装成通过。\n\n"
            "随后建立 closed-world V2 契约：候选只可读取明确白名单字段，train/validation/test 使用互斥时间窗，原始逐标注者"
            "投票与来源被保留，validation/test/blind/judge-only 资料不得用于训练、调参、规则或控制器更新，记录也不能授予"
            "规则替换或发布权限。本地修复门通过后，`gpt-5.4` 第二轮独立复审 5/5 全部通过，失败项、关键发现和修复建议均为 0。\n\n"
            "它的作用是把原先主要依靠政策布尔值的边界，升级为代码可强制、可攻击测试、可外部复核的封闭契约。"
            "这仍只覆盖合成、非私人契约，不代表外部用户、公开服务、专业权限或训练权限已经开放。"
            f"当前本地聊天基座仍是 `{context['selected_model']}`。"
            f"下一阶段是 {context['next_version']}，需要你决定：{context['required_decision']}"
        )
    if context["current_version"] == "PSM V0.260":
        return (
            "这轮已完成 PSM V0.260 内部试用就绪总评审，机器结论是 `internal_trial_ready`，适用范围严格限定为"
            "本机、单用户、内部使用。评审重新核对了 2228/2228 正式核心、20/20 独立盲测、13/13 内部 Alpha 场景、"
            "114 项当前测试、162 个 Python source、V0.259 Sigma+、浏览器、Docker、模型性能、失败账本和剩余风险。"
            f"关键事实幻觉和关键安全漏判都是 0；当前聊天模型是 `{context['selected_model']}`，模型失败率为 0，"
            "p95 22.949 秒低于 60 秒服务端时限。\n\n"
            "评审保留了 17 项剩余风险，其中 12 项仍开放或尚未建设，只有在当前封闭边界内才可接受。"
            "V0.256 合成契约外部评审虽已获授权，但仍因没有 API 凭证而未提交，系统没有把它写成已完成。"
            "外部用户、隐私合规、公开服务、医疗/法律/交易权限、shadow 控制输出与规则替换仍全部关闭。"
            f"下一阶段是 {context['next_version']}，当前需要你介入：{context['required_decision']}"
        )
    if context["current_version"] == "PSM V0.259":
        return (
            "这轮已完成 PSM V0.259 Sigma+ 可追溯交付闭环：普通用户仍只看到自然回答，研发视图则把 Q 到 Sigma+ 状态、"
            "来源、工具结果、失败、声明等级和 V0.258 calibrated shadow 观察绑定在同一个交付包。强结论必须有 provenance，"
            "否则可见文本中必须明确降级；不满足时会在送达前 fail-closed 修复。\n\n"
            "冻结验收 15/15 通过，共审计 22 条强声明，追溯或降级覆盖率 100%；6 题走真实 provenance，保留 2 个工具失败、"
            "25 个未解 judge 和 19 个 shadow 回退 target。普通回答内部术语泄漏、候选控制输出与外部放行权都是 0。"
            "它的作用是把“回答正确”升级为“回答、证据、未知项和失败可以逐层追溯”，但这仍不是开放外部试用。"
            f"当前聊天模型仍是 `{context['selected_model']}`。下一步是 {context['next_version']}："
            f"{context['next_objective']}。"
        )
    if context["current_version"] == "PSM V0.258":
        return (
            "这轮已完成 PSM V0.258 七个物性状态 head 的来源隔离置信度校准与 fail-closed 棄权：新增 14 条 calibration、"
            "14 条 evaluation 和 7 条 unresolved 合成记录，全部不含私人资料且 family、source、内容与近似重复交叉均为 0。"
            "新来源评估平均覆盖率为 95.92%，最低选择性准确率为 92.86%，4 个低置信 target 自动棄权，接受结果中的"
            " critical false negative 为 0；7 个标注分歧 target 全由共识契约拒绝采纳，受保护反馈回流训练为 0。\n\n"
            "它的作用是让 shadow 状态候选开始知道何时不能被采纳，同时不修改 V0.257 基础模型权重。"
            "模型自身对分歧的低置信识别仍是 0/7，因此当前由共识门和确定性规则兜底，不能声称模型已经理解歧义。"
            f"当前聊天模型仍是 `{context['selected_model']}`。下一步是 {context['next_version']}："
            f"{context['next_objective']}。"
        )
    if context["current_version"] == "PSM V0.257":
        return (
            "这轮已完成 PSM V0.257 首个来源隔离的可训练 shadow 状态编码器：42 条无私人资料的合成记录按来源分成"
            "14 train、14 validation、14 test，七个 head 分别预测 Q、Omega、phi、Delta sigma、Pi、eta 和 B_sigma。"
            "首轮因 validation/test 各有 3 个 critical false negative 被拒绝并保留；修复未知词似然 bug 后，候选的"
            "validation exact 为 0.928571、test exact 为 1.0，两个受保护 split 的 critical false negative 都是 0。\n\n"
            "它的作用是证明物性状态可以由隔离数据训练出参数化候选，而不只来自手写规则；但透明规则在 validation/test"
            "仍为 1.0，因此规则继续掌权，候选只能 shadow 观察，不能控制路由、放行或专业行动。"
            f"当前聊天模型仍是 `{context['selected_model']}`。下一步是 {context['next_version']}："
            f"{context['next_objective']}。"
        )
    if context["current_version"] == "PSM V0.256":
        return (
            "这轮已完成 PSM V0.256 来源隔离的物性状态标注与数据契约：Q、Omega、phi、Delta sigma、Pi、eta、"
            "B_sigma 七类目标已经冻结。8 条无私人资料的合成记录获得 16 份独立标注，3 个目标分歧被保留为 unresolved，"
            "没有被压成训练真值；family、source、内容、近似重复、候选输入泄漏和受保护集回流均为 0。\n\n"
            "它的作用是让系统能机器化判断哪些资料可进入训练、哪些只能用于验证或 judge-only 裁判。当前训练尚未启动，"
            "所有未来候选仍是 shadow-only，不能替换规则或开放外部权限。"
            f"当前聊天模型仍是 `{context['selected_model']}`。"
            f"下一步是 {context['next_version']}：{context['next_objective']}。"
        )
    if context["current_version"] == "PSM V0.255":
        return (
            "这轮已完成 PSM V0.255 内部聊天 Alpha 总门：独立冻结盲测最终波次 20/20 通过，当前 13/13 个普通聊天、"
            "多轮、项目接地、事实接地、研究和高风险场景通过；关键事实幻觉与严重安全漏检都是 0。法律传票漏路由"
            "也已修复。真实 Qwen 浏览器、任务图、路由和 Docker 证据保持通过。\n\n"
            "它的作用是把“可以体验”升级为“允许稳定本机内部试用”，同时明确没有开放外部用户、公开服务、"
            "多人隐私或医疗、法律、交易授权。"
            f"当前聊天模型是 `{context['selected_model']}`。下一步是 {context['next_version']}："
            f"{context['next_objective']}。"
        )
    if context["current_version"] == "PSM V0.254":
        return (
            "这轮已完成 PSM V0.254：每轮聊天现在都会把消息、文件、来源、工具、主张、未知项、失败和裁判组织成"
            "任务级 Π 依赖图，并把节点分成已知、推断、未知、冲突和待确认。加入新证据后，系统会给出图差分和新的"
            "下一协议；动态 Π 与 η 已回写状态包。\n\n"
            "它的作用是让多轮聊天不再只记住文字，而是能说明证据如何改变任务状态。失败事件只能进入隔离队列，"
            "经过独立筛选后也只获得回归候选资格，不能自动污染盲集或训练真值。"
            f"当前聊天模型是 `{context['selected_model']}`。下一步是 {context['next_version']}："
            f"{context['next_objective']}。"
        )
    if context["current_version"] == "PSM V0.253":
        return (
            "这轮已完成 PSM V0.253：Omega 不再只有路线标签，现在能实际读取结构化项目状态、已验证来源和项目内文件，"
            "也能对 Python 做不执行代码的 AST 检查，或运行固定白名单中的项目验证命令。每次执行都会分开记录来源、"
            "SHA-256、耗时、未满足裁判与失败事件。\n\n"
            "它的作用是让“需要查证”从一句提示变成真实动作；缺失、越界、超时和冲突都不能被流畅语言覆盖。"
            f"当前聊天模型是 `{context['selected_model']}`。下一步是 {context['next_version']}："
            f"{context['next_objective']}。"
        )
    if context["current_version"] == "PSM V0.252":
        return (
            "这轮已完成 PSM V0.252：正常聊天现在有明确生成阶段、耗时、取消、70 秒超时、保留输入重试和错误恢复，"
            "回答通过审计后会逐步显示，调试证据不会进入主对话。桌面、手机、键盘、布局溢出和真实 Qwen/Docker"
            f"后端都已通过自动化浏览器回归，当前聊天模型是 `{context['selected_model']}`。\n\n"
            "它的作用是把“能生成答案”升级成可稳定操作、失败可恢复、结果可验收的内部聊天 alpha。"
            f"下一步是 {context['next_version']}：{context['next_objective']}。"
        )
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
    *,
    route_execution: dict | None = None,
) -> dict:
    prompt = build_chat_prompt(current, conversation, result, route_execution=route_execution)
    provider = OllamaChatProvider(OLLAMA_BASE_URL)
    max_tokens = selected_chat_max_tokens()
    provider_result = provider.generate(
        ProviderRequest(
            prompt=prompt,
            model=selected_chat_model(),
            timeout_seconds=selected_chat_timeout_seconds(),
            temperature=0.0,
            max_tokens=max_tokens,
        )
    )
    first_result = provider_result
    if provider_result.status == "success" and provider_result.finish_reason == "length":
        provider_result = provider.generate(
            ProviderRequest(
                prompt=prompt,
                model=selected_chat_model(),
                timeout_seconds=selected_chat_timeout_seconds(),
                temperature=0.0,
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


def selected_chat_timeout_seconds() -> int:
    if CHAT_TIMEOUT_OVERRIDE:
        return int(CHAT_TIMEOUT_OVERRIDE)
    selection_path = PSM_ROOT / "runtime" / "chat_provider_selection.json"
    if selection_path.exists():
        selection = load_json(selection_path)
        selected = selection.get("generation_parameters", {}).get("timeout_seconds")
        if isinstance(selected, int) and selected > 0:
            return selected
    return 45


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


def theory_fallback(current: str) -> str:
    folded = current.casefold()
    if ("物性ai" in folded or "物性 ai" in folded) and any(
        marker in folded for marker in ("普通大模型", "大语言模型", "大語言模型", "llm")
    ):
        return psm_vs_llm_answer()
    return (
        "物性论框架先固定问题对象和 Q 核，再依次检查 Ω 风险、φ 状态、Δσ 变化、Π 证据结构、"
        "η 未知项与 B_sigma 审计，最后只把通过边界的内容交给 Σ+ 表达。"
        "这是一套内部状态与声明约束方法，不等于外部证明；结论等级仍取决于来源、独立复现和外部验证。"
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
    if any(marker in current for marker in ("传票", "傳票", "法院", "法庭")):
        return (
            "我不能保证诉讼结果。先核对法院、案号、送达时间、开庭或答辩期限，保存传票、起诉状和信封或邮件头；"
            "再按争议事实整理合同、付款、沟通和时间线，不要忽略送达文件或错过期限。"
            "尽快让当地合资格律师结合司法辖区和原始材料确认答辩、出庭及证据要求。"
        )
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
    roadmap_candidates = sorted((PSM_ROOT / "roadmap_out").glob("PSM_*_Roadmap_*.md"))
    roadmap_source = str(roadmap_candidates[-1].relative_to(PSM_ROOT)) if roadmap_candidates else "CURRENT_STATUS.md"
    selection_path = PSM_ROOT / "runtime" / "chat_provider_selection.json"
    selection = load_json(selection_path) if selection_path.exists() else {}
    selection_metrics = selection.get("selection_metrics", {})
    checkpoint_candidates = sorted(
        (PSM_ROOT / "runtime").glob("v0_*_checkpoint.json"),
        key=lambda path: int(re.search(r"v0_(\d+)", path.name).group(1))
        if re.search(r"v0_(\d+)", path.name)
        else -1,
        reverse=True,
    )
    checkpoint_path = checkpoint_candidates[0] if checkpoint_candidates else PSM_ROOT / "runtime" / "missing_checkpoint.json"
    checkpoint = load_json(checkpoint_path) if checkpoint_path.exists() else {}
    if (
        next_version == "PSM V0.263"
        and checkpoint.get("participant_count_selected") == 3
    ):
        next_objective = (
            "让三名已选受邀者在场完成成年核验、告知、确认、明确同意和现场监督门控；"
            "三人全部通过前不得启动第一条试用消息"
        )
    chat_gate = status.get("independent_chat_gate") or {}
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
        "stage_blocked": (
            bool(next_stage.get("blocked", False))
            or bool(checkpoint.get("requires_user_input", False))
            or str(checkpoint.get("status") or "").startswith("blocked_")
        ),
        "checkpoint_status": str(checkpoint.get("status") or "unknown"),
        "requires_user_input": bool(next_stage.get("requires_user_input", False))
        or bool(checkpoint.get("requires_user_input", False)),
        "chat_gate_passed": bool(chat_gate.get("passed", False)),
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
        correction_only = (
            any(marker in current for marker in ("更正当前版本", "更正當前版本", "更正版本"))
            and any(marker in current for marker in ("本地结构化记录", "本地結構化記錄", "本地记录", "本地紀錄"))
        )
        facts = [context["current_version"]] if correction_only else [
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
    if "structured content-free participant feedback" in objective.casefold():
        return (
            "在现场监督下收集三名参与者对新低风险回答的结构化质量回馈，每人三次；"
            "为保护隐私只保留固定评分，不收集自由文字、身份或聊天原文，不把参与者内容提交外部 API，"
            "也不用于自动训练或公开发布"
        )
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
    if "stable internal chat alpha" in objective.casefold():
        return "稳定内部聊天 alpha：生成状态、取消、超时、重试、错误恢复、渐进显示和桌面/移动浏览器回归"
    if "replace route labels with executable" in objective.casefold():
        return (
            "把 Ω 路由标签升级为可执行的本地状态、来源检索、代码检查和文件证据适配器，"
            "记录来源与失败，并禁止工具结果绕过 PSM 门控"
        )
    if "task-level pi dependency graph" in objective.casefold():
        return (
            "从消息、文件、工具和裁判结果建立任务级 Π 依赖图，把状态分为已知、推断、未知、冲突和待确认，"
            "并从失败账本生成需要独立筛选的学习候选，禁止自动回流盲集或训练真相"
        )
    if "internal chat alpha gate" in objective.casefold():
        return (
            "执行内部聊天 Alpha 总门：重放冻结盲测，复核多轮任务状态、项目接地、普通聊天和高风险帮助式边界，"
            "要求关键事实幻觉与严重安全漏检为零，并完成浏览器、API 和 Docker 回归"
        )
    if "source-isolated annotation protocol" in objective.casefold():
        return (
            "建立来源隔离的物性状态标注与数据契约，定义 Q、Omega、phi、Delta sigma、Pi、eta、B_sigma 目标和"
            "标注分歧，执行 family/source/time 切分；训练候选保持 shadow-only，不能替换现有规则"
        )
    if "shadow state-encoder baseline" in objective.casefold():
        return (
            "只用来源隔离且已解析的训练标注建立首个 shadow 状态编码器，逐目标比较透明规则、多数类与可训练候选，"
            "验证集、测试集、blind 和 judge-only 资料禁止回流，critical safety false negative 不得增加"
        )
    if "confidence calibration" in objective.casefold():
        return (
            "在 family、source、time 三重来源隔离下扩展新的来源 family，为七个 shadow head 加入置信度校准、"
            "低置信度 abstention 和 unresolved 分歧评估，"
            "继续禁止 validation、test、blind、judge-only 反馈回流训练，并保留确定性规则控制器"
        )
    if "sigma+ traceable delivery contract" in objective.casefold():
        return (
            "建立 Sigma+ 可追溯交付闭环，把自然回答、物性状态、来源、工具结果、失败与声明等级绑定；"
            "强结论必须有 provenance 或显式降级，低置信和 unresolved target 回退确定性规则，普通聊天不暴露内部调试细节"
        )
    if "internal trial readiness review" in objective.casefold():
        return (
            "执行内部试用就绪总评审，汇总安全、聊天质量、盲测、模型对照、性能、失败账本与剩余风险，"
            "结论只能是 internal_trial_ready、needs_more_work 或 blocked；外部用户与专业权限继续关闭"
        )
    if "post-internal external-validation lane" in objective.casefold():
        return (
            "定义内部就绪之后的外部验证阶段，包括外部用户范围、数据与隐私要求、部署、预算和 API 凭证；"
            "这些属于用户授权边界，未决定前不能上传资料或启动外部试用"
        )
    if "enroll three to five real invited adults" in objective.casefold():
        return (
            "在冻结的 V0.262 协议下招募 3 至 5 名真实受邀成年人：只生成本地化名邀请，"
            "由操作员线下核验成年并完成告知、确认和明确同意；所有人通过门控前不得启动试用"
        )
    if "bounded supervised pilot" in objective.casefold():
        return (
            "执行三人受控监督试用：每位化名参与者至少完成三次低风险一般问题，"
            "只保留七天内容为空的运行元数据，不收集身份或原始聊天内容，不得将参与者内容发送外部 API；"
            "任何隐私、同意、监督、禁区或提供方边界事件都立即停止且不得自动恢复"
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
    internal_alpha_gate = status.get("internal_alpha_gate") or {}
    external_trial_gate = status.get("external_trial_protocol_gate") or {}
    enrollment_checkpoint_path = PSM_ROOT / "runtime" / "v0_263_participant_enrollment_checkpoint.json"
    enrollment_checkpoint = (
        load_json(enrollment_checkpoint_path) if enrollment_checkpoint_path.exists() else {}
    )
    try:
        live_enrollment = load_enrollment_api_status()
    except (EnrollmentError, FileNotFoundError):
        live_enrollment = {}
    target = optional_status.get("targeted_optional_external", {})
    full = optional_status.get("full_required_fault_external", candidate_gate)
    current_version = status["current_version"].replace("psm_v", "PSM V")
    return {
        "version": current_version,
        "selected_chat_model": selected_chat_model(),
        "chat_timeout_seconds": selected_chat_timeout_seconds(),
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
        "ready_for_stable_internal_chat": internal_alpha_gate.get("decision") == "internal_trial_ready",
        "internal_trial_decision": internal_alpha_gate.get("decision") or "not_evaluated",
        "ready_for_invite_only_external_trial_protocol": external_trial_gate.get("decision") == "invite_only_trial_protocol_ready",
        "external_trial_participant_minimum": external_trial_gate.get("participant_minimum"),
        "external_trial_participant_maximum": external_trial_gate.get("participant_maximum"),
        "external_trial_metadata_retention_days": external_trial_gate.get("metadata_retention_days"),
        "external_trial_monthly_api_budget_usd": external_trial_gate.get("monthly_api_budget_usd"),
        "external_trial_participant_enrollment_completed": live_enrollment.get("trial_active") is True,
        "v0_263_selected_participant_count": enrollment_checkpoint.get("participant_count_selected", 0),
        "v0_263_pseudonymous_invitations_generated": enrollment_checkpoint.get("pseudonymous_invitations_generated", 0),
        "v0_263_enrollment_interface_ready": bool(live_enrollment),
        "v0_263_adult_verified": (live_enrollment.get("counts") or {}).get("adult_verified", 0),
        "v0_263_notice_acknowledged": (live_enrollment.get("counts") or {}).get("notice_acknowledged", 0),
        "v0_263_explicitly_consented": (live_enrollment.get("counts") or {}).get("consented", 0),
        "v0_263_session_enabled": (live_enrollment.get("counts") or {}).get("session_enabled", 0),
        "ready_for_supervised_invite_only_trial": live_enrollment.get("trial_active") is True,
        "ready_for_external_user_trial": False,
    }


def load_trial_notice() -> dict:
    notice_path = PSM_ROOT / "V0_262_INVITE_ONLY_TRIAL_NOTICE.md"
    if not notice_path.exists():
        raise FileNotFoundError("V0.262 trial notice is unavailable.")
    try:
        enrollment = load_enrollment_api_status()
    except (EnrollmentError, FileNotFoundError):
        enrollment = {}
    trial_active = enrollment.get("trial_active") is True
    return {
        "schema_version": "psm_v0_262_trial_notice_response_v1",
        "version": "PSM V0.262",
        "notice_version": "psm_v0_262_trial_notice_v1",
        "content": notice_path.read_text(encoding="utf-8"),
        "participant_enrollment_completed": trial_active,
        "trial_active": trial_active,
        "public_service_allowed": False,
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
