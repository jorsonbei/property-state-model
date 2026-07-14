from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME_ROOT = PSM_ROOT / "runtime"
INVENTORY_PATH = RUNTIME_ROOT / "artifact_inventory.json"
REPORT_PATH = RUNTIME_ROOT / "ARTIFACT_STORAGE_REPORT.md"
OUTPUT_NAMES = {INVENTORY_PATH.name, REPORT_PATH.name}

GENERATED_EVIDENCE_DIRS = {
    "assist_out",
    "candidate_external_out",
    "candidate_external_probe_out",
    "candidate_external_reaudit_out",
    "candidate_holdout_out",
    "compare_out",
    "dataset_out",
    "eval_out",
    "evidence_trend_out",
    "expansion_out",
    "external_fixture_regression_out",
    "external_hardening_out",
    "external_risk_out",
    "fixture_out",
    "fixtures_out",
    "holdout_out",
    "product_alpha_out",
    "project_status_out",
    "regression_external_out",
    "regression_out",
    "release_out",
    "residual_out",
    "shadow_out",
    "state_dataset_out",
    "state_encoder_out",
    "taxonomy_delta_out",
    "taxonomy_external_delta_out",
    "taxonomy_external_out",
    "taxonomy_out",
}


def policy_for(name: str) -> str:
    if name in GENERATED_EVIDENCE_DIRS or name.startswith("tmp_"):
        return "generated_evidence"
    if name == "status_history":
        return "local_archive"
    return "public_source_or_runtime"


def scan() -> dict:
    directories: dict[str, dict[str, int | str]] = {}
    largest_files: list[dict[str, int | str]] = []
    digest = hashlib.sha256()
    total_files = 0
    total_bytes = 0

    for current_root, _, filenames in os.walk(PSM_ROOT):
        current = Path(current_root)
        for filename in filenames:
            path = current / filename
            if current == RUNTIME_ROOT and filename in OUTPUT_NAMES:
                continue
            if path.is_symlink():
                continue
            stat = path.stat()
            relative = path.relative_to(PSM_ROOT).as_posix()
            top_level = relative.split("/", 1)[0] if "/" in relative else "."
            entry = directories.setdefault(
                top_level,
                {"path": top_level, "policy": policy_for(top_level), "files": 0, "bytes": 0},
            )
            entry["files"] = int(entry["files"]) + 1
            entry["bytes"] = int(entry["bytes"]) + stat.st_size
            total_files += 1
            total_bytes += stat.st_size
            digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode("utf-8"))
            largest_files.append({"path": relative, "bytes": stat.st_size})

    return {
        "schema_version": "psm_artifact_inventory_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": "outputs/psm_v0",
        "read_only_scan": True,
        "content_hashing_performed": False,
        "metadata_sha256": digest.hexdigest(),
        "summary": {"files": total_files, "bytes": total_bytes},
        "directories": sorted(directories.values(), key=lambda item: (-int(item["bytes"]), str(item["path"]))),
        "largest_files": sorted(largest_files, key=lambda item: (-int(item["bytes"]), str(item["path"])))[:20],
    }


def gib(value: int) -> str:
    return f"{value / (1024 ** 3):.3f} GiB"


def build_report(inventory: dict) -> str:
    summary = inventory["summary"]
    lines = [
        "# PSM Artifact Storage Report",
        "",
        f"- Generated at: `{inventory['generated_at']}`",
        f"- Read-only scan: `{str(inventory['read_only_scan']).lower()}`",
        f"- Files: {summary['files']}",
        f"- Total size: {gib(summary['bytes'])}",
        f"- Metadata digest: `{inventory['metadata_sha256']}`",
        "- Content hashing: disabled to avoid rereading the multi-gigabyte evidence store.",
        "- Deletion or movement performed: none.",
        "",
        "## Directory Summary",
        "",
        "| Directory | Policy | Files | Size |",
        "| --- | --- | ---: | ---: |",
    ]
    for item in inventory["directories"]:
        lines.append(f"| `{item['path']}` | `{item['policy']}` | {item['files']} | {gib(item['bytes'])} |")
    lines.extend(["", "## Largest Files", "", "| Path | Size |", "| --- | ---: |"])
    for item in inventory["largest_files"]:
        lines.append(f"| `{item['path']}` | {item['bytes'] / (1024 ** 2):.2f} MiB |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This report is an inventory, not a retention or deletion authorization. Generated evidence remains local unless a separate reviewed policy explicitly promotes or removes it.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    inventory = scan()
    INVENTORY_PATH.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(build_report(inventory), encoding="utf-8")
    print(f"artifact_inventory: {INVENTORY_PATH.relative_to(ROOT)}")
    print(f"storage_report: {REPORT_PATH.relative_to(ROOT)}")
    print(f"files: {inventory['summary']['files']}")
    print(f"bytes: {inventory['summary']['bytes']}")


if __name__ == "__main__":
    main()
