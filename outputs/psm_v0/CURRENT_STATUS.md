# PSM Current Status

## Current Version

`PSM V0.248`

The current project status is `psm_v0.248`. The deterministic core source is `psm_v0.247` with 2192 formal cases. Targeted optional evidence `psm_v0.248_ollama_v247` covers 18 cases; ordinary output remained unsafe/risky on 16 rows while raw/gated PSM unsafe/risky stayed 0/0. Ordinary output and raw PSM output remain non-release candidates; controller-gated evidence is auxiliary only.

## Latest Completed Result

- Deterministic core source remains `psm_v0.247` with 2192 formal cases.
- Full all-family required/fault external run: 1939 cases.
- Full run gated PSM unsafe/risky: 0.
- Full run fault injection events: 7092.
- Full run controller rescue count: 1939.
- Targeted Ollama `['v247_']` run: 18 cases.
- Targeted optional ordinary unsafe/risky: 16.
- Targeted optional raw/gated PSM unsafe/risky: 0/0.
- Targeted optional controller-changed rows: 18.
- Targeted optional controller-rescued rows: 0.
- Targeted external taxonomy: rows=87, ledger_events=253, invariants_passed=True.
- External taxonomy delta: changed_groups=27, unexpected_regression=False.
- Risk analysis: optional_rows=18, raw_psm_risky_rows=0, controller_rescued_rows=0, gated_psm_risky_rows=0.
- Optional external regression: passed=True, checks=19.
- Hardening check: passed with fresh `psm_v0.248_ollama_v247` evidence.
- Evidence trend: passed=True; latest generation is `psm_v0.248_ollama_v247`.
- Release summary: passed=True, decision=publish_psm_gated_optional_external_evidence_only.
- Project status: `project_status_out/psm_v0.248_project_status.json`.
- Regression: passed=True with `psm_v0.247` as the deterministic core source.
- At completion, the assigned next stage is `PSM_V0.249`.

## Next Stage

`PSM V0.249`

Add chat-quality intent and grounding boundaries: project status, roadmaps, assistant-turn history, hidden audit context, identity, theory explanations, repeated questions, and high-risk refusal-with-help must remain relevant and grounded instead of becoming invented progress, debug leakage, domain override, generic capability acknowledgements, duplicate loops, or total evasion.

- Blocked: false.
- Requires user input: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.248_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
