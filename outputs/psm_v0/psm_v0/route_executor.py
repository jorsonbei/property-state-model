from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


ALLOWED_FILE_SUFFIXES = {".csv", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
EXPLICIT_EVIDENCE_MARKERS = (
    "查证",
    "查證",
    "核验",
    "核驗",
    "来源",
    "來源",
    "证据",
    "證據",
    "读取",
    "讀取",
    "打开文件",
    "打開文件",
    "检查当前项目",
    "檢查當前項目",
    "运行项目测试",
    "執行項目測試",
    "make check",
)
UNSATISFIED_STATUSES = {"blocked", "conflict", "failed", "missing_evidence", "timeout"}
_LEDGER_LOCK = threading.Lock()


@dataclass(frozen=True)
class RouteContext:
    question: str
    intent: str
    domain: str
    route: str
    allowed_statement_level: str
    required_judges: tuple[str, ...]
    project_root: Path
    psm_root: Path
    verified_facts: tuple[str, ...] = ()
    verified_sources: tuple[str, ...] = ()
    timeout_seconds: float = 20.0


class RouteAdapter(Protocol):
    name: str

    def applicable(self, context: RouteContext) -> bool: ...

    def execute(self, context: RouteContext) -> dict: ...


@dataclass
class AdapterResult:
    adapter: str
    status: str
    facts: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    claims: dict[str, str] = field(default_factory=dict)
    provenance: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "adapter": self.adapter,
            "status": self.status,
            "facts": self.facts,
            "sources": self.sources,
            "claims": self.claims,
            "provenance": self.provenance,
            "failures": self.failures,
            "details": self.details,
            "duration_ms": self.duration_ms,
        }


class ProjectStatusAdapter:
    name = "local_project_status"

    def applicable(self, context: RouteContext) -> bool:
        return context.intent in {"project_results", "project_status", "roadmap"}

    def execute(self, context: RouteContext) -> dict:
        started = time.monotonic()
        source_path, payload = _load_project_status(context.psm_root)
        if payload is None:
            return _result(
                self.name,
                "missing_evidence",
                started,
                failures=[_failure("project_status_missing", "No structured project status was found.")],
            )
        current = str(payload.get("current_version") or "unknown")
        next_stage = payload.get("next_stage") or {}
        next_version = str(next_stage.get("version") or "undefined")
        core_cases = int(payload.get("core_metrics", {}).get("eval", {}).get("cases") or 0)
        source = _relative_source(source_path, context.project_root)
        return _result(
            self.name,
            "success",
            started,
            facts=[current, next_version, str(core_cases)],
            sources=[source],
            claims={
                "project.current_version": current,
                "project.next_version": next_version,
                "project.core_cases": str(core_cases),
            },
            provenance=[_file_provenance(source_path, context.project_root)],
            details={"read_only": True, "next_objective": str(next_stage.get("objective") or "")},
        )


class VerifiedSourceAdapter:
    name = "verified_source_retrieval"

    def applicable(self, context: RouteContext) -> bool:
        return bool(context.verified_facts or context.verified_sources)

    def execute(self, context: RouteContext) -> dict:
        started = time.monotonic()
        provenance = [
            {
                "kind": "verified_kernel" if source.startswith("verified_kernel:") else "external_source",
                "source": source,
                "read_only": True,
                "external": source.startswith(("http://", "https://")),
            }
            for source in context.verified_sources
        ]
        return _result(
            self.name,
            "success",
            started,
            facts=list(context.verified_facts),
            sources=list(context.verified_sources),
            provenance=provenance,
            details={"source_count": len(context.verified_sources)},
        )


class FileEvidenceAdapter:
    name = "local_file_evidence"

    def applicable(self, context: RouteContext) -> bool:
        return bool(extract_file_candidates(context.question))

    def execute(self, context: RouteContext) -> dict:
        started = time.monotonic()
        facts: list[str] = []
        sources: list[str] = []
        provenance: list[dict] = []
        failures: list[dict] = []
        for token in extract_file_candidates(context.question):
            path, error = resolve_project_file(token, context.project_root, context.psm_root)
            if error:
                failures.append(_failure(error, f"Cannot read requested path: {token}", path=token))
                continue
            assert path is not None
            if path.stat().st_size > 256_000:
                failures.append(
                    _failure("file_too_large", "Requested file exceeds the 256 KB evidence limit.", path=token)
                )
                continue
            text = path.read_text(encoding="utf-8")
            source = _relative_source(path, context.project_root)
            facts.append(f"{source}: {_summarize_file(path, text)}")
            sources.append(source)
            provenance.append(_file_provenance(path, context.project_root))
        if facts and failures:
            status = "partial"
        elif facts:
            status = "success"
        elif any(item["code"] in {"path_outside_project", "file_type_blocked"} for item in failures):
            status = "blocked"
        else:
            status = "missing_evidence"
        return _result(
            self.name,
            status,
            started,
            facts=facts,
            sources=sources,
            provenance=provenance,
            failures=failures,
            details={"requested_paths": extract_file_candidates(context.question), "read_only": True},
        )


class CodeCheckAdapter:
    name = "sandboxed_code_check"

    def applicable(self, context: RouteContext) -> bool:
        return bool(_python_snippets(context.question)) or _requests_project_check(context.question)

    def execute(self, context: RouteContext) -> dict:
        started = time.monotonic()
        snippets = _python_snippets(context.question)
        if snippets:
            failures = []
            for index, snippet in enumerate(snippets, start=1):
                try:
                    ast.parse(snippet)
                except SyntaxError as exc:
                    failures.append(
                        _failure(
                            "python_syntax_error",
                            f"Python snippet {index} failed syntax parsing at line {exc.lineno}: {exc.msg}",
                        )
                    )
            status = "success" if not failures else "failed"
            return _result(
                self.name,
                status,
                started,
                facts=[f"python_snippets_parsed: {len(snippets)}"] if not failures else [],
                sources=["inline_user_code"],
                claims={"code.python_syntax": "passed" if not failures else "failed"},
                provenance=[
                    {
                        "kind": "inline_static_analysis",
                        "source": "inline_user_code",
                        "sha256": hashlib.sha256("\n".join(snippets).encode("utf-8")).hexdigest(),
                        "read_only": True,
                        "external": False,
                    }
                ],
                failures=failures,
                details={"mode": "python_ast", "executed_user_code": False},
            )

        project_verifier = context.project_root / "scripts" / "verify_project.py"
        if project_verifier.exists():
            command = [sys.executable, "scripts/verify_project.py"]
            command_id = "verify_project"
            evidence_path = project_verifier
        else:
            command = [sys.executable, "-m", "psm_v0.runtime_verifier"]
            command_id = "verify_runtime"
            evidence_path = context.psm_root / "psm_v0" / "runtime_verifier.py"
        try:
            completed = _run_allowed_command(command, context.project_root, context.timeout_seconds)
        except subprocess.TimeoutExpired:
            return _result(
                self.name,
                "timeout",
                started,
                failures=[_failure("tool_timeout", "The fixed project verification command timed out.")],
                details={"mode": "project_verify", "command_id": command_id, "timeout_seconds": context.timeout_seconds},
            )
        output = (completed.stdout + "\n" + completed.stderr).strip()
        if completed.returncode != 0:
            return _result(
                self.name,
                "failed",
                started,
                sources=[_relative_source(evidence_path, context.project_root)],
                provenance=[_file_provenance(evidence_path, context.project_root)],
                failures=[_failure("project_check_failed", "The fixed project verification command failed.")],
                details={"mode": "project_verify", "command_id": command_id, "output_tail": output[-1600:]},
            )
        return _result(
            self.name,
            "success",
            started,
            facts=["project_check: passed"],
            sources=[_relative_source(evidence_path, context.project_root)],
            claims={"code.project_check": "passed"},
            provenance=[_file_provenance(evidence_path, context.project_root)],
            details={
                "mode": "project_verify",
                "command_id": command_id,
                "allowlisted_command": True,
                "output_tail": output[-1600:],
            },
        )


def execute_route(
    question: str,
    *,
    intent: str,
    pipeline_result: dict,
    project_root: Path,
    psm_root: Path,
    verified_facts: tuple[str, ...] = (),
    verified_sources: tuple[str, ...] = (),
    ledger_path: Path | None = None,
    adapters: tuple[RouteAdapter, ...] | None = None,
    timeout_seconds: float = 20.0,
) -> dict:
    route = pipeline_result["route"]
    context = RouteContext(
        question=question,
        intent=intent,
        domain=pipeline_result["packet"]["domain"],
        route=str(route["route"]),
        allowed_statement_level=str(route["allowed_statement_level"]),
        required_judges=tuple(route.get("required_judges") or ()),
        project_root=project_root.resolve(),
        psm_root=psm_root.resolve(),
        verified_facts=verified_facts,
        verified_sources=verified_sources,
        timeout_seconds=timeout_seconds,
    )
    selected = adapters or (
        ProjectStatusAdapter(),
        VerifiedSourceAdapter(),
        FileEvidenceAdapter(),
        CodeCheckAdapter(),
    )
    results = [AdapterResult(**adapter.execute(context)) for adapter in selected if adapter.applicable(context)]
    payload = aggregate_route_results(context, results)
    events = build_route_failure_events(payload, pipeline_result["packet"].get("packet_id"))
    payload["failure_events"] = events
    if ledger_path and events:
        append_route_failure_ledger(ledger_path, events)
    return payload


def aggregate_route_results(context: RouteContext, results: list[AdapterResult]) -> dict:
    conflicts = _claim_conflicts(results)
    statuses = {result.status for result in results}
    success_count = sum(result.status in {"success", "partial"} for result in results)
    if conflicts:
        status = "conflict"
    elif "blocked" in statuses:
        status = "blocked"
    elif "timeout" in statuses:
        status = "timeout"
    elif "failed" in statuses:
        status = "failed" if not success_count else "partial"
    elif success_count:
        status = "partial" if "partial" in statuses or "missing_evidence" in statuses else "success"
    elif results:
        status = "missing_evidence"
    elif context.route == "direct_language":
        status = "not_required"
    else:
        status = "not_executed"

    facts = _unique(item for result in results for item in result.facts)
    sources = _unique(item for result in results for item in result.sources)
    provenance = [item for result in results for item in result.provenance]
    failures = [item for result in results for item in result.failures]
    failures.extend(
        _failure("evidence_conflict", f"Conflicting values for {key}: {values}", claim=key)
        for key, values in conflicts.items()
    )
    source_or_tool_passed = status in {"success", "partial"} and bool(sources)
    satisfied = []
    unresolved = []
    for judge in context.required_judges:
        if judge == "source_or_tool_check" and source_or_tool_passed:
            satisfied.append(judge)
        elif judge == "bsigma_audit":
            satisfied.append(judge)
        elif judge == "boundary_statement":
            satisfied.append(judge)
        else:
            unresolved.append(judge)
    explicit = any(marker in context.question.casefold() for marker in EXPLICIT_EVIDENCE_MARKERS)
    return {
        "schema_version": "psm_route_execution_v1",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": sum(result.duration_ms for result in results),
        "route": context.route,
        "status": status,
        "domain": context.domain,
        "allowed_statement_level": context.allowed_statement_level,
        "explicit_evidence_request": explicit,
        "adapters": [result.to_dict() for result in results],
        "facts": facts,
        "sources": sources,
        "provenance": provenance,
        "failures": failures,
        "conflicts": conflicts,
        "required_judges": list(context.required_judges),
        "satisfied_judges": satisfied,
        "unresolved_judges": unresolved,
        "can_support_answer": status not in {"blocked", "conflict", "failed", "timeout"}
        and not (explicit and status in {"missing_evidence", "not_executed"}),
        "can_support_strong_claim": status == "success" and not unresolved,
        "external_release_authority": False,
        "rule_replacement_allowed": False,
    }


def build_route_failure_events(payload: dict, packet_id: str | None) -> list[dict]:
    if payload["status"] not in UNSATISFIED_STATUSES and not (
        payload["explicit_evidence_request"] and payload["status"] == "not_executed"
    ):
        return []
    now = datetime.now(timezone.utc).isoformat()
    failures = payload["failures"] or [
        _failure("route_not_executed", "No applicable evidence adapter executed the requested route.")
    ]
    return [
        {
            "ts": now,
            "event_type": "route_execution_failure",
            "route": payload["route"],
            "status": payload["status"],
            "domain": payload["domain"],
            "packet_id": packet_id,
            "adapter": failure.get("adapter"),
            "code": failure["code"],
            "reason": failure["message"],
            "external_release_authority": False,
        }
        for failure in failures
    ]


def append_route_failure_ledger(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LEDGER_LOCK, path.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def extract_file_candidates(question: str) -> list[str]:
    candidates = re.findall(r"`([^`]+)`", question)
    candidates.extend(re.findall(r"(?<![\w])([\w./\-]+\.(?:csv|json|md|py|toml|txt|ya?ml))(?![\w])", question, re.I))
    return _unique(
        token.strip().strip('"\'，。；：,;:()[]{}')
        for token in candidates
        if Path(token.strip().strip('"\'，。；：,;:()[]{}')).suffix.casefold() in ALLOWED_FILE_SUFFIXES
    )


def resolve_project_file(token: str, project_root: Path, psm_root: Path) -> tuple[Path | None, str | None]:
    raw = Path(token).expanduser()
    candidates = [raw] if raw.is_absolute() else [project_root / raw, psm_root / raw]
    path = next((candidate.resolve() for candidate in candidates if candidate.exists()), candidates[0].resolve())
    try:
        path.relative_to(project_root.resolve())
    except ValueError:
        return None, "path_outside_project"
    if path.suffix.casefold() not in ALLOWED_FILE_SUFFIXES:
        return None, "file_type_blocked"
    if not path.is_file():
        return None, "file_not_found"
    return path, None


def _load_project_status(psm_root: Path) -> tuple[Path, dict | None]:
    status_dir = psm_root / "project_status_out"
    status_paths = sorted(status_dir.glob("psm_v0.*_project_status.json"), key=_status_version)
    if status_paths:
        path = status_paths[-1]
        return path, json.loads(path.read_text(encoding="utf-8"))
    snapshot = psm_root / "runtime" / "current_runtime_snapshot.json"
    if snapshot.exists():
        payload = json.loads(snapshot.read_text(encoding="utf-8"))
        return snapshot, payload.get("project_status")
    return snapshot, None


def _status_version(path: Path) -> int:
    match = re.search(r"psm_v0\.(\d+)_project_status", path.name)
    return int(match.group(1)) if match else -1


def _python_snippets(question: str) -> list[str]:
    return [match.strip() for match in re.findall(r"```(?:python|py)\s*\n(.*?)```", question, re.I | re.S) if match.strip()]


def _requests_project_check(question: str) -> bool:
    lower = question.casefold()
    has_project = any(marker in lower for marker in ("当前项目", "當前項目", "本地项目", "本地項目", "这个项目", "這個項目"))
    has_check = any(marker in lower for marker in ("检查", "檢查", "运行测试", "執行測試", "跑测试", "跑測試", "make check"))
    return has_project and has_check


def _run_allowed_command(command: list[str], cwd: Path, timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(cwd / "outputs" / "psm_v0")}
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )


def _summarize_file(path: Path, text: str) -> str:
    if path.suffix.casefold() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return "invalid JSON"
        if isinstance(payload, dict):
            scalar_items = [f"{key}={value}" for key, value in payload.items() if isinstance(value, (str, int, float, bool))]
            keys = ", ".join(list(payload)[:20])
            summary = "; ".join(scalar_items[:12])
            return f"JSON keys: {keys}" + (f"; values: {summary}" if summary else "")
        return f"JSON {type(payload).__name__} with {len(payload) if hasattr(payload, '__len__') else 0} items"
    compact = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return compact[:1400] + ("..." if len(compact) > 1400 else "")


def _file_provenance(path: Path, project_root: Path) -> dict:
    return {
        "kind": "local_file",
        "source": _relative_source(path, project_root),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
        "read_only": True,
        "external": False,
    }


def _relative_source(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _result(
    adapter: str,
    status: str,
    started: float,
    *,
    facts: list[str] | None = None,
    sources: list[str] | None = None,
    claims: dict[str, str] | None = None,
    provenance: list[dict] | None = None,
    failures: list[dict] | None = None,
    details: dict | None = None,
) -> dict:
    return AdapterResult(
        adapter=adapter,
        status=status,
        facts=facts or [],
        sources=sources or [],
        claims=claims or {},
        provenance=provenance or [],
        failures=[{**failure, "adapter": failure.get("adapter") or adapter} for failure in failures or []],
        details=details or {},
        duration_ms=max(0, round((time.monotonic() - started) * 1000)),
    ).to_dict()


def _failure(code: str, message: str, **details: str) -> dict:
    return {"code": code, "message": message, **details}


def _claim_conflicts(results: list[AdapterResult]) -> dict[str, list[str]]:
    values: dict[str, set[str]] = {}
    for result in results:
        for key, value in result.claims.items():
            values.setdefault(key, set()).add(str(value))
    return {key: sorted(items) for key, items in values.items() if len(items) > 1}


def _unique(items) -> list[str]:
    return list(dict.fromkeys(str(item) for item in items if str(item)))
