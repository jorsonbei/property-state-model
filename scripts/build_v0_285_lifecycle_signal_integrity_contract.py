#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "psm_v0" / "benchmarks" / "v0_285_lifecycle_signal_integrity_contract.json"


def main() -> None:
    cases = [
        {"case_id": "S01", "family": "same_session_reset_no_resurrection"},
        {"case_id": "S02", "family": "same_session_reload_no_resurrection"},
        {"case_id": "S03", "family": "stale_instance_no_resurrection"},
        {"case_id": "S04", "family": "unknown_event_ignored"},
        {"case_id": "S05", "family": "message_replay_idempotent"},
        {"case_id": "S06", "family": "hash_tombstones_bounded"},
        {"case_id": "S07", "family": "concurrent_session_isolation"},
        {"case_id": "S08", "family": "zero_user_statement_disk_writes"},
    ]
    canonical = json.dumps(cases, sort_keys=True, separators=(",", ":"))
    value = {
        "schema_version": "psm_v0_285_lifecycle_signal_integrity_contract_v1",
        "version": "PSM_V0.285-candidate",
        "source_version": "PSM_V0.284",
        "frozen": True,
        "synthetic_only": True,
        "case_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "cases": cases,
        "requirements": {
            "memory_resurrection_events_allowed": 0,
            "cross_session_leaks_allowed": 0,
            "maximum_tombstones": 128,
            "raw_session_ids_in_tombstones_allowed": 0,
            "user_statement_disk_writes_allowed": 0,
            "external_release_authority": False,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"contract: {OUT.relative_to(ROOT)}")
    print(f"cases: {len(cases)}")


if __name__ == "__main__":
    main()
