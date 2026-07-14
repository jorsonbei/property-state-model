from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.252_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.253_project_status.json"
ROUTE_REPORT = PSM_ROOT / "runtime" / "v0_253_route_execution_report.json"
BROWSER_REPORT = PSM_ROOT / "runtime" / "v0_253_browser_regression" / "report.json"
DOCKER_REPORT = PSM_ROOT / "runtime" / "v0_253_docker_verification.json"
CHECKPOINT = PSM_ROOT / "runtime" / "v0_253_route_checkpoint.json"
MANIFEST = PSM_ROOT / "runtime" / "v0_253_route_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_source_status() -> dict:
    if SOURCE_STATUS.exists():
        return read_json(SOURCE_STATUS)
    return read_json(PSM_ROOT / "runtime" / "current_runtime_snapshot.json")["project_status"]


def validate(route: dict, browser: dict, docker: dict) -> None:
    summary = route.get("summary") or {}
    if route.get("passed") is not True or summary.get("cases") != summary.get("passed"):
        raise SystemExit("V0.253 route execution report is not passing.")
    if int(summary.get("real_adapter_class_count") or 0) < 4:
        raise SystemExit("V0.253 has fewer than four real route adapter classes.")
    if int(summary.get("failure_ledger_events") or 0) < 4:
        raise SystemExit("V0.253 failure ledger does not cover required fault classes.")
    if summary.get("external_judge_unresolved_on_high_risk") is not True:
        raise SystemExit("V0.253 high-risk external-judge boundary was not retained.")
    if browser.get("passed") is not True:
        raise SystemExit("V0.253 browser regression is not passing.")
    if browser.get("real_backend", {}).get("ran") is not True:
        raise SystemExit("V0.253 real backend browser smoke did not run.")
    if browser.get("route_evidence", {}).get("ran") is not True:
        raise SystemExit("V0.253 route evidence browser smoke did not run.")
    if browser.get("route_evidence", {}).get("internal_route_fields_hidden_from_answer") is not True:
        raise SystemExit("V0.253 route fields leaked into the normal answer.")
    if docker.get("passed") is not True or docker.get("code_route", {}).get("command_id") != "verify_runtime":
        raise SystemExit("V0.253 Docker runtime route did not pass.")


def main() -> None:
    source = load_source_status()
    route = read_json(ROUTE_REPORT)
    browser = read_json(BROWSER_REPORT)
    docker = read_json(DOCKER_REPORT)
    validate(route, browser, docker)

    checkpoint = {
        "schema_version": "psm_v0_253_route_checkpoint_v1",
        "current_promoted_version": "PSM_V0.253",
        "target_version": "PSM_V0.253",
        "target_promoted": True,
        "status": "promoted_v0_254_dynamic_pi_eta_in_progress",
        "requires_user_input": False,
        "route_gate": {
            "route_report": "runtime/v0_253_route_execution_report.json",
            "browser_report": "runtime/v0_253_browser_regression/report.json",
            "docker_report": "runtime/v0_253_docker_verification.json",
            "cases": route["summary"]["cases"],
            "passed": route["summary"]["passed"],
            "real_adapter_classes": route["summary"]["real_adapter_classes"],
            "failure_ledger_events": route["summary"]["failure_ledger_events"],
            "browser_base_url": browser["base_url"],
            "docker_runtime_check": docker["runtime"],
            "high_risk_external_judge_unresolved": True,
        },
        "completed_engineering": [
            "uniform route execution schema with status, facts, sources, claims, provenance, timing, and failures",
            "local structured project-status adapter",
            "verified knowledge and source adapter",
            "project-root-confined read-only file evidence adapter",
            "Python AST and fixed-command sandboxed code-check adapter",
            "host full-project verifier and container runtime verifier",
            "explicit missing, blocked, timeout, and conflict failure ledger",
            "route failure transparency and false-verification quality gate",
            "debug-only route status, source count, and failure count",
            "host and Docker real-backend browser regression",
        ],
        "release_boundary": {
            "external_user_trial_allowed": False,
            "external_judge_satisfied_for_arbitrary_high_risk_requests": False,
            "rule_replacement_allowed": False,
            "internal_local_demo_only": True,
            "v0_253_promoted": True,
        },
        "required_decision": (
            "当前不需要用户决定。继续执行 PSM V0.254 的动态 Pi、eta、证据冲突和失败学习候选施工；"
            "失败不得自动流入冻结盲集或训练真相。"
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.253"
    target["previous_formal_version"] = "psm_v0.252"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "real_omega_routes_and_tool_evidence"
    target["route_execution_gate"] = checkpoint["route_gate"]
    target["next_stage"] = {
        "version": "PSM_V0.254",
        "objective": (
            "Build a task-level Pi dependency graph from messages, files, tools, and judge results; classify known, "
            "inferred, unknown, conflicting, and pending state; derive failure-learning candidates without automatic "
            "blind-set or training backflow."
        ),
        "blocked": False,
        "requires_user_input": False,
    }
    target.setdefault("primary_artifacts", {}).update(
        {
            "route_execution_gate": "runtime/v0_253_route_execution_report.json",
            "route_browser_gate": "runtime/v0_253_browser_regression/report.json",
            "route_docker_gate": "runtime/v0_253_docker_verification.json",
            "route_checkpoint": "runtime/v0_253_route_checkpoint.json",
            "project_status": "project_status_out/psm_v0.253_project_status.json",
        }
    )
    write_json(TARGET_STATUS, target)

    manifest = {
        "schema_version": "psm_v0_253_route_promotion_manifest_v1",
        "version": "PSM_V0.253",
        "promoted_at": "2026-07-14",
        "promoted": True,
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "route_gate": checkpoint["route_gate"],
        "boundaries": checkpoint["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"checkpoint: {CHECKPOINT.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
