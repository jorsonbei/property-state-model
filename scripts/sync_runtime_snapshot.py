from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
RUNTIME_ROOT = PSM_ROOT / "runtime"


def version_number(path: Path) -> int:
    prefix = "psm_v0."
    suffix = "_project_status.json"
    name = path.name
    if not name.startswith(prefix) or not name.endswith(suffix):
        return -1
    try:
        return int(name[len(prefix) : -len(suffix)])
    except ValueError:
        return -1


def load_statuses() -> list[dict]:
    paths = sorted((PSM_ROOT / "project_status_out").glob("psm_v0.*_project_status.json"), key=version_number)
    if not paths:
        raise SystemExit("No project status artifacts found.")
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]


def load_readiness() -> dict:
    candidates = [
        PSM_ROOT / "product_alpha_out" / "psm_v0.235_chat_alpha_readiness.json",
        PSM_ROOT / "product_alpha_out" / "psm_v0.230_product_alpha_readiness.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return {
        "ready_for_internal_local_demo": False,
        "ready_for_internal_chat_demo": False,
        "ready_for_external_user_trial": False,
    }


def main() -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    statuses = load_statuses()
    project_status = statuses[-1]
    optional_status = next(
        (status for status in reversed(statuses) if "targeted_optional_external" in status),
        project_status,
    )
    payload = {
        "schema_version": "psm_public_runtime_snapshot_v1",
        "project_status": project_status,
        "optional_project_status": optional_status,
        "chat_readiness": load_readiness(),
    }
    path = RUNTIME_ROOT / "current_runtime_snapshot.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"runtime_snapshot: {path.relative_to(ROOT)}")
    print(f"current_version: {payload['project_status']['current_version']}")


if __name__ == "__main__":
    main()
