from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


SCHEMA_VERSION = "psm_training_dataset_v0.7"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export PSM comparison artifacts to a training-ready JSONL dataset.")
    parser.add_argument("--eval-dir", type=Path, default=Path("eval_out"))
    parser.add_argument("--compare-dir", type=Path, default=Path("compare_out"))
    parser.add_argument("--outdir", type=Path, default=Path("dataset_out"))
    parser.add_argument("--dataset-name", default="psm_v0.7_training.jsonl")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    records = build_records(args.eval_dir, args.compare_dir)
    dataset_path = args.outdir / args.dataset_name
    dataset_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest = build_manifest(records, dataset_path)
    manifest_path = args.outdir / "psm_v0.7_dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"records: {len(records)}")
    print(f"dataset: {dataset_path}")
    print(f"manifest: {manifest_path}")


def build_records(eval_dir: Path, compare_dir: Path) -> list[dict]:
    records = []
    for compare_path in sorted(compare_dir.glob("*.compare.json")):
        compare = json.loads(compare_path.read_text(encoding="utf-8"))
        case_id = compare["case"]["id"]
        eval_path = eval_dir / f"{case_id}.result.json"
        if not eval_path.exists():
            raise FileNotFoundError(f"missing eval result for {case_id}: {eval_path}")
        eval_result = json.loads(eval_path.read_text(encoding="utf-8"))
        records.append(build_record(case_id, compare_path, eval_path, compare, eval_result))
    return records


def build_record(case_id: str, compare_path: Path, eval_path: Path, compare: dict, eval_result: dict) -> dict:
    result = eval_result["result"]
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    ordinary_audit = compare["ordinary_audit"]
    raw_psm_audit = compare["psm_raw_audit"]
    gated_psm_audit = compare["psm_audit"]
    ordinary_response = compare["ordinary_response"]
    psm_response = compare["psm_response"]

    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": case_id,
        "split": "seed",
        "source": {
            "case_id": case_id,
            "compare_path": str(compare_path),
            "eval_path": str(eval_path),
            "adapter": psm_response.get("adapter"),
            "model": psm_response.get("model"),
        },
        "input": {
            "user_request": compare["case"]["request"],
            "domain": packet["domain"],
            "phi_state": packet["phi_state"],
            "q_core": packet["q_core"],
            "omega": packet["omega"],
            "delta_sigma": packet["delta_sigma"],
            "pi_cavity": packet["pi_cavity"],
            "eta": packet["eta"],
            "external_judges": packet["external_judges"],
            "statement_level": packet["statement_level"],
        },
        "labels": {
            "q_status": q_audit["status"],
            "risk_level": packet["omega"]["risk_level"],
            "route": route["route"],
            "statement_level": packet["statement_level"],
            "bsigma_status": bsigma["status"],
            "bsigma_risks": sorted({item["risk"] for item in packet.get("bsigma_risks", [])}),
            "gate_score": eval_result["gate_score"]["score"],
            "ordinary_status": ordinary_audit["status"],
            "ordinary_net_risk": ordinary_audit["net_risk"],
            "raw_psm_status": raw_psm_audit["status"],
            "raw_psm_net_risk": raw_psm_audit["net_risk"],
            "gated_psm_status": gated_psm_audit["status"],
            "gated_psm_net_risk": gated_psm_audit["net_risk"],
            "ordinary_unsafe_or_risky": ordinary_audit["status"] in {"unsafe", "risky"},
            "raw_psm_unsafe_or_risky": raw_psm_audit["status"] in {"unsafe", "risky"},
            "gated_psm_unsafe_or_risky": gated_psm_audit["status"] in {"unsafe", "risky"},
            "controller_changed_output": compare["controller_changed_output"],
            "controller_rescued": compare["controller_rescued"],
            "controller_risk_reduction": compare["controller_risk_reduction"],
            "gated_risk_reduction_vs_ordinary": compare["risk_reduction"],
        },
        "outputs": {
            "ordinary_candidate": compare["ordinary_candidate"],
            "raw_psm_candidate": compare["psm_raw_candidate"],
            "gated_psm_candidate": compare["psm_candidate"],
        },
        "audits": {
            "q_audit": q_audit,
            "route": route,
            "bsigma_audit": bsigma,
            "ordinary_candidate_audit": ordinary_audit,
            "raw_psm_candidate_audit": raw_psm_audit,
            "gated_psm_candidate_audit": gated_psm_audit,
            "gate_score": eval_result["gate_score"],
        },
        "metrics": {
            "ordinary_latency_ms": compare["ordinary_latency_ms"],
            "psm_latency_ms": compare["psm_latency_ms"],
            "ordinary_adapter_ok": compare["ordinary_adapter_ok"],
            "psm_adapter_ok": compare["psm_adapter_ok"],
            "ordinary_model": ordinary_response.get("model"),
            "psm_model": psm_response.get("model"),
        },
    }


def build_manifest(records: list[dict], dataset_path: Path) -> dict:
    domains = Counter(record["input"]["domain"] for record in records)
    q_statuses = Counter(record["labels"]["q_status"] for record in records)
    risks = Counter(record["labels"]["risk_level"] for record in records)
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_path": str(dataset_path),
        "records": len(records),
        "domains": dict(sorted(domains.items())),
        "q_statuses": dict(sorted(q_statuses.items())),
        "risk_levels": dict(sorted(risks.items())),
        "ordinary_total_net_risk": sum(record["labels"]["ordinary_net_risk"] for record in records),
        "raw_psm_total_net_risk": sum(record["labels"]["raw_psm_net_risk"] for record in records),
        "gated_psm_total_net_risk": sum(record["labels"]["gated_psm_net_risk"] for record in records),
        "controller_rescue_count": sum(1 for record in records if record["labels"]["controller_rescued"]),
        "controller_risk_reduction": sum(record["labels"]["controller_risk_reduction"] for record in records),
    }


if __name__ == "__main__":
    main()
