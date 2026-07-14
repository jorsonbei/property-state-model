from __future__ import annotations

import argparse
import json
from pathlib import Path

from .failure_ledger import append_ledger, build_ledger_events
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PSM V0 state audit.")
    parser.add_argument("--text", help="Raw user request.")
    parser.add_argument("--input", type=Path, help="Path to a text file containing the request.")
    parser.add_argument("--outdir", type=Path, default=Path("run_output"), help="Output directory.")
    parser.add_argument("--case-id", help="Optional case id for ledger entries.")
    parser.add_argument("--ledger", type=Path, help="Optional JSONL failure ledger path.")
    args = parser.parse_args()

    if not args.text and not args.input:
        raise SystemExit("Provide --text or --input.")
    if args.text and args.input:
        raise SystemExit("Use only one of --text or --input.")

    text = args.text if args.text is not None else args.input.read_text(encoding="utf-8")
    result = run_pipeline(text)
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    report = result["report"]

    args.outdir.mkdir(parents=True, exist_ok=True)
    packet_path = args.outdir / "state_packet.json"
    report_path = args.outdir / "sigma_report.md"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    if args.ledger:
        append_ledger(args.ledger, build_ledger_events(result, case_id=args.case_id))

    print(f"state_packet: {packet_path}")
    print(f"sigma_report: {report_path}")
    print(f"q_status: {q_audit['status']}")
    print(f"route: {route['route']}")
    print(f"bsigma_status: {bsigma['status']}")


if __name__ == "__main__":
    main()
