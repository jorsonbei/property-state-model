from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME = PSM_ROOT / "runtime"
SOURCE_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.255_project_status.json"
TARGET_STATUS = PSM_ROOT / "project_status_out" / "psm_v0.256_project_status.json"
GATE = RUNTIME / "v0_256_annotation_contract_gate.json"
ISOLATION = RUNTIME / "v0_256_source_isolation_report.json"
EXTERNAL_PACKAGE = RUNTIME / "v0_256_external_contract_review_package.json"
CHECKPOINT = RUNTIME / "v0_256_annotation_contract_checkpoint.json"
MANIFEST = RUNTIME / "v0_256_annotation_contract_promotion_manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preferred_report(v256: Path, v255: Path) -> tuple[Path, dict]:
    path = v256 if v256.exists() else v255
    return path, read_json(path)


def validate(gate: dict, isolation: dict, external: dict, browser: dict, docker: dict) -> None:
    if gate.get("passed") is not True or gate.get("decision") != "contract_ready_training_not_started":
        raise SystemExit("V0.256 annotation contract gate is not passing.")
    if not all((gate.get("checks") or {}).values()):
        raise SystemExit("V0.256 annotation contract gate contains a failed check.")
    metrics = gate.get("metrics") or {}
    zero_metrics = (
        "source_overlap",
        "family_overlap",
        "content_overlap",
        "near_duplicate_overlap",
        "candidate_input_leaks",
        "protected_backflow",
    )
    if any(metrics.get(name) != 0 for name in zero_metrics):
        raise SystemExit("V0.256 isolation metrics are not clean.")
    if metrics.get("unresolved_targets", 0) <= 0:
        raise SystemExit("V0.256 did not exercise preserved annotator disagreement.")
    if isolation.get("passed") is not True:
        raise SystemExit("V0.256 source isolation report is not passing.")
    if external.get("privacy", {}).get("synthetic_only") is not True:
        raise SystemExit("V0.256 external review package is not synthetic-only.")
    if external.get("privacy", {}).get("contains_private_data") is not False:
        raise SystemExit("V0.256 external review package contains private data.")
    if browser.get("passed") is not True or browser.get("real_backend", {}).get("ran") is not True:
        raise SystemExit("V0.256 browser regression is not passing.")
    if docker.get("passed") is not True:
        raise SystemExit("V0.256 Docker verification is not passing.")
    boundaries = gate.get("boundaries") or {}
    if boundaries.get("training_started") is not False:
        raise SystemExit("V0.256 incorrectly claims training started.")
    if boundaries.get("candidate_shadow_only") is not True:
        raise SystemExit("V0.256 candidate is not shadow-only.")
    if boundaries.get("rule_replacement_allowed") is not False:
        raise SystemExit("V0.256 opened rule replacement.")


def main() -> None:
    source = read_json(SOURCE_STATUS)
    gate = read_json(GATE)
    isolation = read_json(ISOLATION)
    external = read_json(EXTERNAL_PACKAGE)
    browser_path, browser = preferred_report(
        RUNTIME / "v0_256_browser_regression" / "report.json",
        RUNTIME / "v0_255_browser_regression" / "report.json",
    )
    docker_path, docker = preferred_report(
        RUNTIME / "v0_256_docker_verification.json",
        RUNTIME / "v0_255_docker_verification.json",
    )
    validate(gate, isolation, external, browser, docker)

    annotation_gate = {
        "decision": gate["decision"],
        "passed": True,
        **gate["metrics"],
        "training_started": False,
        "candidate_shadow_only": True,
        "rule_replacement_allowed": False,
        "external_review_submission_status": external["submission_status"],
        "contract": "benchmarks/v0_256_state_annotation_contract.json",
        "source_isolation_report": "runtime/v0_256_source_isolation_report.json",
        "browser_report": str(browser_path.relative_to(PSM_ROOT)),
        "docker_report": str(docker_path.relative_to(PSM_ROOT)),
    }
    checkpoint = {
        "schema_version": "psm_v0_256_annotation_contract_checkpoint_v1",
        "current_promoted_version": "PSM_V0.256",
        "target_version": "PSM_V0.256",
        "target_promoted": True,
        "status": "promoted_v0_257_shadow_encoder_baseline_in_progress",
        "requires_user_input": False,
        "annotation_contract_gate": annotation_gate,
        "completed_engineering": [
            "frozen Q, Omega, phi, Delta sigma, Pi, eta, and B_sigma annotation targets",
            "independent per-target vote distributions with unresolved disagreement retained",
            "family, source, and time grouped split assignment",
            "exact-content and near-duplicate cross-split contamination audit",
            "candidate feature view with target and judge fields removed",
            "validation and test backflow sealed at zero",
            "shadow-only training export preview with training not started",
            "synthetic non-private external review package prepared under user authorization",
        ],
        "release_boundary": {
            "stable_internal_local_chat_allowed": True,
            "external_user_trial_allowed": False,
            "training_started": False,
            "candidate_shadow_only": True,
            "blind_or_test_training_truth": False,
            "judge_only_separate": True,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
            "v0_256_promoted": True,
        },
        "required_decision": (
            "当前不需要用户决定。继续执行 PSM V0.257：继承来源隔离与 family/source/time split，"
            "只用已解析 train 标注建立透明规则基线与首个可训练状态编码候选；全程 shadow-only，按目标和 split "
            "分开报告，critical safety false negative 不得增加，且不替换现有规则。"
        ),
    }
    write_json(CHECKPOINT, checkpoint)

    target = copy.deepcopy(source)
    target["current_version"] = "psm_v0.256"
    target["previous_formal_version"] = "psm_v0.255"
    target["source_evidence_version"] = "psm_v0.251"
    target["completed_result"] = "source_isolated_annotation_and_dataset_contract"
    target["annotation_contract_gate"] = annotation_gate
    target["next_stage"] = {
        "version": "PSM_V0.257",
        "objective": (
            "Build the first source-isolated shadow state-encoder baseline from resolved training-only annotations; "
            "compare transparent rule, majority, and trainable candidates per target and protected split; keep critical "
            "safety false negatives non-increasing; and prohibit validation, test, judge-only, or blind feedback from training."
        ),
        "blocked": False,
        "requires_user_input": False,
    }
    target.setdefault("primary_artifacts", {}).update(
        {
            "state_annotation_contract": "benchmarks/v0_256_state_annotation_contract.json",
            "annotation_contract_gate": "runtime/v0_256_annotation_contract_gate.json",
            "source_isolation_report": "runtime/v0_256_source_isolation_report.json",
            "shadow_training_preview": "runtime/v0_256_shadow_training_export_preview.json",
            "external_contract_review_package": "runtime/v0_256_external_contract_review_package.json",
            "annotation_contract_checkpoint": "runtime/v0_256_annotation_contract_checkpoint.json",
            "project_status": "project_status_out/psm_v0.256_project_status.json",
        }
    )
    write_json(TARGET_STATUS, target)

    manifest = {
        "schema_version": "psm_v0_256_annotation_contract_promotion_manifest_v1",
        "version": "PSM_V0.256",
        "promoted_at": "2026-07-14",
        "promoted": True,
        "decision": gate["decision"],
        "formal_core_source": "PSM_V0.251",
        "formal_core_records": source["core_metrics"]["eval"]["cases"],
        "annotation_contract_gate": annotation_gate,
        "boundaries": checkpoint["release_boundary"],
        "next_stage": target["next_stage"],
    }
    write_json(MANIFEST, manifest)
    print(f"status: {TARGET_STATUS.relative_to(ROOT)}")
    print(f"checkpoint: {CHECKPOINT.relative_to(ROOT)}")
    print(f"manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
