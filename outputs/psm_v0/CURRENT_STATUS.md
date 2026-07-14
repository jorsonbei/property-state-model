# PSM Current Status

## Current Version

`PSM V0.253`

The current project status is `psm_v0.253`. V0.253 promotes executable Omega route evidence while retaining `psm_v0.251` as the formal 2228-record core evidence source. Required/fault candidate gating remains 1975 cases with gated PSM unsafe/risky at 0.

## Latest Completed Result

- Added `psm_route_execution_v1`: adapter status, facts, sources, claims, provenance, SHA-256, timing, failures, satisfied judges, and unresolved judges are separate fields.
- Added four real read-only/local adapter classes: structured project status, verified sources, project-confined file evidence, and sandboxed code checks.
- Python snippets are AST-parsed without execution; project commands are fixed allowlist entries, never user-supplied shell commands.
- Host code checks run the full project verifier; Docker runs a smaller runtime verifier against the packaged snapshot and core routes.
- Path traversal, missing sources, tool timeout, and evidence conflicts fail closed and enter a JSONL failure ledger.
- Explicit evidence failures must remain visible in the user-facing answer; unsupported claims of completed verification fail chat quality audit.
- Route evaluation: 10/10 cases passed across four real adapter classes and four failure-ledger classes.
- Browser regression passed on Docker with real `qwen3.5:9b`; route status/source/failure counts appear only in the closed-by-default debug panel.
- Docker runtime verification passed with 54 Python files parsed, regression retained, and high-risk external-judge requirements unresolved rather than fabricated.
- External user trial, arbitrary high-risk external judgment, and rule replacement remain closed.

## Next Stage

`PSM V0.254`

Build dynamic Pi and eta state from actual task evidence:

- construct a task-level dependency graph from messages, files, route adapters, tool results, and judge results;
- classify nodes and claims as known, inferred, unknown, conflicting, or pending;
- update the graph when new evidence arrives and explain what changed;
- derive failure-learning candidates from the ledger only through independent screening;
- prohibit automatic backflow into frozen blind sets or training truth.

- Blocked: false.
- Requires user input: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.253_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Route checkpoint: `runtime/v0_253_route_checkpoint.json`.
- Route evaluation: `runtime/v0_253_route_execution_report.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
