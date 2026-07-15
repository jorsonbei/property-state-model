# PSM Current Status

## Current Version

`PSM V0.261`

The current project status is `psm_v0.261`. V0.261 completes the authorized synthetic external contract-review loop while retaining `psm_v0.251` as the formal 2228-record core evidence source and preserving the V0.260 local single-user `internal_trial_ready` boundary.

## Latest Completed Result

- The first OpenAI external review completed and returned `fail`, with five failed checks and three critical findings; this failure remains retained as evidence.
- A closed-world V2 annotation contract now rejects unknown fields at every governed object level and exposes only an exact candidate-readable projection.
- Train, validation, and test use mutually exclusive time windows; source groups crossing a boundary are rejected.
- Raw per-annotator votes and source annotation IDs are retained; unresolved records cannot become training truth.
- Validation, test, blind, judge-only, adjudication, evaluation, and model-output artifacts cannot flow into training, tuning, model selection, prompt/rule updates, or controller updates.
- Ten local mutation and boundary checks pass with zero candidate-input leaks and zero protected backflow, including nested leaf-type, malformed-object, and extra-target rejection.
- The final independent `gpt-5.4-2026-03-05` rejudge passes 5/5 questions with zero failed checks, critical findings, or recommended repairs.
- Current project verification passes 125 tests and parses 169 Python sources.
- The API credential is retrieved from Keychain and is not persisted in project artifacts.
- External users, privacy-compliance claims, public service, professional authority, training authority, rule replacement, and external release authority remain closed.

## Next Stage

`PSM V0.262`

Define and authorize an external-user trial protocol:

- decide whether to start external-user trial preparation and define participant scope;
- define allowed data classes and data-processing/privacy requirements;
- define privacy notice, consent, retention, deletion, and incident handling;
- choose deployment mode and budget;
- keep external access and public service closed until the user-owned protocol is explicitly approved.

- Blocked: true.
- Requires user input: true.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.261_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Initial failed external review: `runtime/v0_261_openai_external_contract_judge_attempt_1_failed.json`.
- Intermediate passing review before leaf-type hardening: `runtime/v0_261_openai_external_contract_judge_attempt_2_passed_pre_leaf_hardening.json`.
- Repaired contract: `benchmarks/v0_261_state_annotation_contract_v2.json`.
- Local repair gate: `runtime/v0_261_annotation_contract_repair_gate.json`.
- Final passing external review: `runtime/v0_261_openai_external_contract_judge.json`.
- Promotion checkpoint: `runtime/v0_261_external_contract_checkpoint.json`.
- Current execution roadmap: `roadmap_out/PSM_External_Validation_Roadmap_V0.261_to_V0.262.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
