from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

from .chat_prompt import build_chat_prompt, sanitize_model_answer
from .chat_provider import OllamaChatProvider, ProviderRequest
from .chat_quality_auditor import audit_chat_answer
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a blind local chat-model bakeoff.")
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--ollama-base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--max-tokens", type=int, default=360)
    parser.add_argument("--outdir", type=Path, default=Path("model_bakeoff_out"))
    parser.add_argument(
        "--selection-config",
        type=Path,
        default=Path("runtime/chat_provider_selection.json"),
    )
    args = parser.parse_args()

    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    candidate_map = {
        f"candidate_{chr(ord('a') + index)}": model
        for index, model in enumerate(args.models)
    }
    provider = OllamaChatProvider(args.ollama_base_url)
    rows = []
    for candidate_id, model in candidate_map.items():
        for case in benchmark["cases"]:
            row = run_case(
                provider,
                candidate_id,
                model,
                case,
                benchmark["latency_target_ms"],
                args.timeout_seconds,
                args.max_tokens,
            )
            rows.append(row)
            print(
                f"{candidate_id}/{case['id']}: status={row['transport_status']}, "
                f"score={row['score']}, duration_ms={row['duration_ms']}",
                flush=True,
            )

    summaries = {
        candidate_id: summarize_candidate(
            [row for row in rows if row["candidate_id"] == candidate_id],
            benchmark["latency_target_ms"],
        )
        for candidate_id in candidate_map
    }
    winner = max(
        summaries,
        key=lambda candidate_id: (
            summaries[candidate_id]["mean_score"],
            -summaries[candidate_id]["failure_rate"],
            -summaries[candidate_id]["median_latency_ms"],
        ),
    )
    ranked = sorted(
        summaries,
        key=lambda candidate_id: (
            summaries[candidate_id]["mean_score"],
            -summaries[candidate_id]["failure_rate"],
            -summaries[candidate_id]["median_latency_ms"],
        ),
        reverse=True,
    )
    benchmark_sha256 = hashlib.sha256(args.benchmark.read_bytes()).hexdigest()
    result = {
        "schema_version": "psm_chat_model_bakeoff_result_v1",
        "version": benchmark["version"],
        "benchmark": str(args.benchmark),
        "benchmark_sha256": benchmark_sha256,
        "blind_scoring": benchmark.get("blind_scoring") is True,
        "candidate_map": candidate_map,
        "summaries": summaries,
        "ranked_candidates": ranked,
        "selected_candidate": winner,
        "selected_model": candidate_map[winner],
        "generation_parameters": {
            "timeout_seconds": args.timeout_seconds,
            "max_tokens": args.max_tokens,
        },
        "rows": rows,
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    result_path = args.outdir / "psm_v0.250_chat_model_bakeoff.json"
    report_path = args.outdir / "PSM_V0.250_Chat_Model_Bakeoff_Report.md"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_report(result), encoding="utf-8")

    selection = {
        "schema_version": "psm_chat_provider_selection_v1",
        "version": benchmark["version"],
        "selected_model": candidate_map[winner],
        "fallback_model": eligible_fallback_model(ranked[1:], summaries, candidate_map),
        "benchmark_sha256": benchmark_sha256,
        "generation_parameters": result["generation_parameters"],
        "selection_metrics": summaries[winner],
        "boundary": {
            "project_status_and_roadmap_bypass_model": True,
            "deterministic_fallback_retained": True,
            "external_user_trial_allowed": False,
        },
    }
    args.selection_config.parent.mkdir(parents=True, exist_ok=True)
    args.selection_config.write_text(json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"cases: {len(benchmark['cases'])}")
    print(f"models: {len(candidate_map)}")
    for candidate_id in ranked:
        summary = summaries[candidate_id]
        print(
            f"{candidate_id}: score={summary['mean_score']:.4f}, "
            f"median_ms={summary['median_latency_ms']}, failures={summary['failures']}"
        )
    print(f"selected_candidate: {winner}")
    print(f"selected_model: {candidate_map[winner]}")
    print(f"result: {result_path}")
    print(f"selection: {args.selection_config}")


def run_case(
    provider: OllamaChatProvider,
    candidate_id: str,
    model: str,
    case: dict,
    latency_target_ms: int,
    timeout_seconds: int,
    max_tokens: int,
) -> dict:
    conversation = case["messages"]
    current = next(item["content"] for item in reversed(conversation) if item["role"] == "user")
    pipeline_result = run_pipeline(current)
    prompt = build_chat_prompt(current, conversation, pipeline_result)
    transport = provider.generate(
        ProviderRequest(
            prompt=prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )
    )
    answer, reasoning_leak = sanitize_model_answer(transport.answer)
    quality = audit_chat_answer(
        current,
        answer,
        intent=case["intent"],
        grounding_facts=case.get("grounding_facts", []),
        previous_assistant_answers=[
            item["content"] for item in conversation[:-1] if item["role"] == "assistant"
        ],
    )
    expected_groups = case.get("expected_any_groups", [])
    boundary_groups = case.get("boundary_any_groups", [])
    expected_passes = [contains_any(answer, group) for group in expected_groups]
    boundary_passes = [contains_any(answer, group) for group in boundary_groups]
    forbidden_hits = [marker for marker in case.get("forbidden_markers", []) if marker in answer]
    available = transport.status == "success" and bool(answer)
    expected_coverage = sum(expected_passes) / len(expected_passes) if expected_passes else 1.0
    boundary_coverage = sum(boundary_passes) / len(boundary_passes) if boundary_passes else 1.0
    chinese = chinese_ratio(answer)
    latency_pass = transport.duration_ms < latency_target_ms
    score = (
        0.15 * float(available)
        + 0.30 * expected_coverage
        + 0.20 * float(quality["status"] == "pass")
        + 0.10 * float(not forbidden_hits)
        + 0.10 * min(chinese / 0.55, 1.0)
        + 0.10 * boundary_coverage
        + 0.05 * float(latency_pass)
    )
    return {
        "candidate_id": candidate_id,
        "case_id": case["id"],
        "transport_status": transport.status,
        "duration_ms": transport.duration_ms,
        "answer": answer,
        "error": transport.error,
        "reasoning_leak_removed": reasoning_leak,
        "quality_status": quality["status"],
        "quality_score": quality["score"],
        "expected_coverage": round(expected_coverage, 4),
        "boundary_coverage": round(boundary_coverage, 4),
        "forbidden_hits": forbidden_hits,
        "chinese_ratio": round(chinese, 4),
        "latency_target_passed": latency_pass,
        "score": round(score, 4),
    }


def summarize_candidate(rows: list[dict], latency_target_ms: int) -> dict:
    durations = sorted(row["duration_ms"] for row in rows)
    failures = sum(row["transport_status"] != "success" for row in rows)
    empty_visible_answers = sum(not row["answer"] for row in rows)
    return {
        "cases": len(rows),
        "mean_score": round(statistics.fmean(row["score"] for row in rows), 4),
        "quality_pass_rate": round(
            sum(row["quality_status"] == "pass" for row in rows) / len(rows),
            4,
        ),
        "mean_expected_coverage": round(
            statistics.fmean(row["expected_coverage"] for row in rows),
            4,
        ),
        "mean_boundary_coverage": round(
            statistics.fmean(row["boundary_coverage"] for row in rows),
            4,
        ),
        "failures": failures,
        "failure_rate": round(failures / len(rows), 4),
        "empty_visible_answers": empty_visible_answers,
        "median_latency_ms": int(statistics.median(durations)),
        "p95_latency_ms": durations[max(0, math.ceil(len(durations) * 0.95) - 1)],
        "latency_target_ms": latency_target_ms,
        "median_latency_target_passed": statistics.median(durations) < latency_target_ms,
        "reasoning_leak_rows": sum(row["reasoning_leak_removed"] for row in rows),
    }


def contains_any(text: str, markers: list[str]) -> bool:
    lowered = text.casefold()
    return any(marker.casefold() in lowered for marker in markers)


def eligible_fallback_model(
    runner_up_ids: list[str],
    summaries: dict[str, dict],
    candidate_map: dict[str, str],
) -> str | None:
    for candidate_id in runner_up_ids:
        summary = summaries[candidate_id]
        if (
            summary["failure_rate"] == 0
            and summary["median_latency_target_passed"]
            and summary["reasoning_leak_rows"] == 0
        ):
            return candidate_map[candidate_id]
    return None


def chinese_ratio(text: str) -> float:
    chinese = sum("\u4e00" <= char <= "\u9fff" for char in text)
    ascii_letters = sum(char.isascii() and char.isalpha() for char in text)
    total = chinese + ascii_letters
    return chinese / total if total else 0.0


def build_report(result: dict) -> str:
    lines = [
        "# PSM V0.250 Chat Model Bakeoff Report",
        "",
        f"- Benchmark SHA256: `{result['benchmark_sha256']}`",
        f"- Blind scoring: `{str(result['blind_scoring']).lower()}`",
        f"- Selected candidate: `{result['selected_candidate']}`",
        f"- Selected model after unblinding: `{result['selected_model']}`",
        f"- Generation parameters: `{result['generation_parameters']}`",
        "",
        "## Candidate Summary",
        "",
    ]
    for candidate_id in result["ranked_candidates"]:
        summary = result["summaries"][candidate_id]
        lines.extend(
            [
                f"### {candidate_id}",
                "",
                f"- Mean score: {summary['mean_score']}",
                f"- Quality pass rate: {summary['quality_pass_rate']}",
                f"- Expected coverage: {summary['mean_expected_coverage']}",
                f"- Boundary coverage: {summary['mean_boundary_coverage']}",
                f"- Median latency: {summary['median_latency_ms']} ms",
                f"- P95 latency: {summary['p95_latency_ms']} ms",
                f"- Failures: {summary['failures']}",
                f"- Empty visible answers after sanitation: {summary['empty_visible_answers']}",
                f"- Reasoning leak rows removed: {summary['reasoning_leak_rows']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- The score is a local engineering comparison on a frozen, authored benchmark.",
            "- It is not an open-domain intelligence claim or external-user release approval.",
            "- Project status and roadmap answers continue to bypass model generation.",
            "- Deterministic fallback remains mandatory on timeout, empty output, or rejected output.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
