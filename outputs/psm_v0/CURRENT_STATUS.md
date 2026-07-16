# PSM Current Status

## Current Version

`PSM V0.270`

V0.270 is promoted. The formal 2228-record evidence core remains `PSM V0.251`; V0.270 adds source-isolated multi-turn reference, correction, topic-switch, and constraint-persistence evidence without changing the formal core.

## Latest Promoted Result

- 12/12 frozen multi-turn cases pass across assistant reference, user-history state, correction priority, and constraint accumulation.
- The first run recorded 5 failures before repair; the append-only failure ledger remains retained.
- Two domain-label corrections and one missing line-count check are retained as transparent evaluator errata.
- Assistant-history state contamination and stale-constraint violations: 0.
- V0.269 separately passes 21/21 repeated task runs with zero provider or deterministic drift; local p50/p95 are 23 ms/16.771 s.
- 189 unit and contract tests pass after the V0.271 local repair.
- Desktop/mobile browser and host/Docker boundaries pass; public and external release remain closed.

## V0.271 External Review

- One authorized source-isolated `gpt-5.4` review was completed over 12 synthetic multi-turn conversations.
- External verdict: `fail`.
- Failed items: `M07`, `M08`.
- M07 over-answered a version correction with unrequested status and release details.
- M08 over-answered a request that explicitly asked to confirm only the corrected conclusion.
- Both findings now pass local repair checks with exact direct answers.
- External rejudge completed: false.
- Monthly API budget: USD 20 reserved / USD 20 limit.
- Required decision: approve an additional USD 4 synthetic rejudge budget, or stop V0.271 external rejudging.

## Evidence Boundary

- V0.269/V0.270 evidence is internally authored and synthetic; it is not human or independent blind evidence.
- The V0.271 external judgment is independent semantic review of synthetic content only.
- Human participants, human feedback, participant-content API calls, and evaluation-to-training backflow: 0.
- Deterministic rules remain authoritative; shadow models cannot control route, risk, release, or professional action.
- Public service, production readiness, rule replacement, professional authority, and external release authority: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.270_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- V0.270 contract/report/gate: `benchmarks/v0_270_multiturn_constraint_contract.json`, `runtime/v0_270_multiturn_constraint_report.json`, `runtime/v0_270_multiturn_constraint_gate.json`.
- V0.270 initial failures and errata: `runtime/v0_270_multiturn_initial_failure_ledger.json`, `benchmarks/v0_270_multiturn_constraint_errata.json`.
- V0.270 browser/Docker: `runtime/v0_270_multiturn_browser_regression/report.json`, `runtime/v0_270_multiturn_docker_boundary.json`.
- V0.271 original package/judge: `runtime/v0_271_external_multiturn_review_package.json`, `runtime/v0_271_openai_external_multiturn_judge.json`.
- V0.271 local repairs/repaired candidate: `runtime/v0_271_external_multiturn_repair_report.json`, `runtime/v0_271_external_multiturn_repaired_candidate.json`.
- Active blocker checkpoint: `runtime/v0_271_external_multiturn_checkpoint.json`.
- Current roadmap: `roadmap_out/PSM_V0.270_to_V0.271_External_Multiturn_Roadmap.md`.

Version history remains in independent snapshots under `status_history/`; it is not embedded recursively here.
