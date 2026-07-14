from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


SCHEMA_VERSION = "psm_state_encoder_dataset_v0.20"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export state-encoder dataset from PSM eval outputs.")
    parser.add_argument("--eval-dir", type=Path, default=Path("eval_out"))
    parser.add_argument("--outdir", type=Path, default=Path("state_dataset_out"))
    parser.add_argument("--stem", default="psm_v0.20")
    parser.add_argument("--schema-version", default=None)
    parser.add_argument("--dataset-name", default=None)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    schema_version = args.schema_version or f"psm_state_encoder_dataset_{args.stem.replace('psm_', '')}"
    dataset_name = args.dataset_name or f"{args.stem}_state_encoder.jsonl"
    records = build_records(args.eval_dir, schema_version)
    assign_splits(records)
    dataset_path = args.outdir / dataset_name
    dataset_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest = build_manifest(records, dataset_path, schema_version)
    manifest_path = args.outdir / f"{args.stem}_state_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"records: {len(records)}")
    print(f"dataset: {dataset_path}")
    print(f"manifest: {manifest_path}")


def build_records(eval_dir: Path, schema_version: str) -> list[dict]:
    records = []
    for eval_path in sorted(eval_dir.glob("*.result.json")):
        payload = json.loads(eval_path.read_text(encoding="utf-8"))
        case = payload["case"]
        result = payload["result"]
        packet = result["packet"]
        q_audit = result["q_audit"]
        route = result["route"]
        bsigma = result["bsigma_audit"]
        risks = sorted({item["risk"] for item in packet.get("bsigma_risks", [])})
        records.append(
            {
                "schema_version": schema_version,
                "record_id": case["id"],
                "split": "unassigned",
                "source": {
                    "case_id": case["id"],
                    "eval_path": str(eval_path),
                    "source_path": case.get("_source_path"),
                },
                "input": {
                    "user_request": case["request"],
                    "domain": packet["domain"],
                    "phi_state": packet["phi_state"],
                    "q_core": packet["q_core"],
                    "omega_observed": packet["omega"],
                    "delta_sigma": packet["delta_sigma"],
                    "pi_cavity": packet["pi_cavity"],
                    "eta": packet["eta"],
                    "external_judges_observed": packet["external_judges"],
                    "statement_level_observed": packet["statement_level"],
                },
                "labels": {
                    "q_status": q_audit["status"],
                    "risk_level": packet["omega"]["risk_level"],
                    "route": route["route"],
                    "bsigma_status": bsigma["status"],
                    "bsigma_risks": risks,
                    "statement_level": packet["statement_level"],
                    "gate_score": payload["gate_score"]["score"],
                },
                "audits": {
                    "q_findings": q_audit["findings"],
                    "q_required_actions": q_audit["required_actions"],
                    "route_required_judges": route["required_judges"],
                    "bsigma_items": bsigma["items"],
                    "gate_score": payload["gate_score"],
                },
            }
        )
    return records


def assign_splits(records: list[dict]) -> None:
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in records:
        buckets[(record["input"]["domain"], record["labels"]["risk_level"])].append(record)

    for bucket_records in buckets.values():
        bucket_records.sort(key=lambda item: item["record_id"])
        n = len(bucket_records)
        if n == 1:
            bucket_records[0]["split"] = "train"
        elif n == 2:
            bucket_records[0]["split"] = "train"
            bucket_records[1]["split"] = "validation"
        else:
            bucket_records[0]["split"] = "validation"
            bucket_records[1]["split"] = "test"
            for record in bucket_records[2:]:
                record["split"] = "train"


def build_manifest(records: list[dict], dataset_path: Path, schema_version: str) -> dict:
    return {
        "schema_version": schema_version,
        "dataset_path": str(dataset_path),
        "records": len(records),
        "splits": dict(sorted(Counter(record["split"] for record in records).items())),
        "domains": dict(sorted(Counter(record["input"]["domain"] for record in records).items())),
        "risk_levels": dict(sorted(Counter(record["labels"]["risk_level"] for record in records).items())),
        "q_statuses": dict(sorted(Counter(record["labels"]["q_status"] for record in records).items())),
        "routes": dict(sorted(Counter(record["labels"]["route"] for record in records).items())),
        "bsigma_statuses": dict(sorted(Counter(record["labels"]["bsigma_status"] for record in records).items())),
    }


if __name__ == "__main__":
    main()
