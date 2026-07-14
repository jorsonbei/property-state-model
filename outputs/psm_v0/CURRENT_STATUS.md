# PSM Current Status

## Current Version

`PSM V0.249`

The current project status is `psm_v0.249`. It promoted `chat_quality_intent_grounding_boundary_adversarial` into the formal core, bringing the formal dataset to 2210 records. Required/fault candidate gating covers 1957 cases with gated PSM unsafe/risky at 0.

## Latest Completed Result

- Built `case_packs/v0_249_chat_quality_intent_grounding_boundary_adversarial_cases.json`.
- Standalone validation: 18/18 passed, including candidate-audit checks.
- Promoted the pack into `cases/v0_249_chat_quality_intent_grounding_boundary_adversarial_cases.json`.
- Core eval: 2210/2210 passed.
- State dataset: 2210 records, errors=0, warnings=0.
- State encoder candidate: exact_match=1.000, B_sigma exact_match=1.000, micro_f1=1.000.
- Admission gate: passed=True, observed={'exact_match': 1.0, 'micro_f1': 1.0, 'critical_false_negatives': 0}.
- Shadow replacement boundary: ledger_events=0, replacement_boundary_passed=True.
- Candidate-assisted mode: override_events=0, drift_present=False, rule_replacement_allowed=false.
- Holdout no-retrain ledger events: 0 on `v249_`.
- Required candidate-output gate: 1957 cases, clean=True, gated PSM unsafe/risky=0.
- Fault injection events: 7148.
- Controller rescue count: 1957.
- Candidate taxonomy: rows=5886, ledger_events=18062, invariants_passed=True.
- Candidate regression fixtures: coverage_passed=True, fixtures=6.
- Taxonomy delta: changed_groups=19, unexpected_regression=False.
- Project status: `project_status_out/psm_v0.249_project_status.json`.
- Regression: passed=True with explicit taxonomy-expansion allowance.
- At completion, the assigned next stage is `PSM_V0.250`.

## Next Stage

`PSM V0.250`

refresh full required/fault external evidence and targeted optional Ollama/controller evidence for `v249_`.

- Blocked: false.
- Requires user input: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.249_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
