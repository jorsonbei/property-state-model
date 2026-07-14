# PSM Current Status

## Current Version

`PSM V0.259`

The current project status is `psm_v0.259`. V0.259 promotes traceable Sigma+ candidate delivery while retaining `psm_v0.251` as the formal 2228-record core evidence source, V0.255 stable internal local chat, the V0.256 annotation contract, the frozen V0.257 shadow baseline, and V0.258 calibrated fail-closed abstention.

## Latest Completed Result

- `/api/chat` now returns a `sigma_plus_delivery` packet with a minimal natural `user_view` and a separate developer trace.
- The developer trace binds Q through Sigma+ state, statement audit, provenance, tool results, failures, unresolved judges, task graph, and calibrated shadow observations.
- Strong claims require provenance or a downgrade marker already present in the visible answer. Unsupported claims fail closed before delivery and are re-audited.
- The frozen synthetic non-private evaluation passes 15/15 cases and audits 22 strong claims with 1.0 minimum provenance-or-downgrade coverage.
- Six cases exercise provenance; two tool failure events and 25 unresolved judges remain visible to developers.
- Nineteen calibrated shadow targets fall back to deterministic rules. Candidate-controlled output remains 0/15.
- Ordinary-chat internal debug leakage and external release authority are both 0.
- Base weights and shadow training feedback remain unchanged. External user trial, privacy compliance, public service, professional authority, and rule replacement remain closed.

## Next Stage

`PSM V0.260`

Run the internal trial readiness review:

- freeze and consolidate safety, chat quality, blind-set, model-comparison, performance, failure-ledger, and residual-risk evidence;
- verify artifact versions, timestamps, and release boundaries are mutually consistent;
- issue only `internal_trial_ready`, `needs_more_work`, or `blocked`;
- rerun API, desktop, mobile, and Docker evidence;
- do not automatically open external users, privacy compliance, public service, or professional authority.

- Blocked: false.
- Requires user input: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.259_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Sigma+ checkpoint: `runtime/v0_259_sigma_plus_checkpoint.json`.
- Sigma+ gate: `runtime/v0_259_sigma_plus_gate.json`.
- Sigma+ metrics: `runtime/v0_259_sigma_plus_metrics.json`.
- Sigma+ frozen evaluation: `runtime/v0_259_sigma_plus_evaluation.jsonl`.
- Sigma+ residual risks: `runtime/v0_259_sigma_plus_residual_risks.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
