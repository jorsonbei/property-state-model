# PSM Current Status

## Current Version

`PSM V0.251`

The current project status is `psm_v0.251`. It promoted `independent_chat_golden_blind_set_boundary_adversarial` into the formal core, bringing the formal dataset to 2228 records. Required/fault candidate gating covers 1975 cases with gated PSM unsafe/risky at 0.

## Latest Completed Result

- The externally authored, frozen Wave G blind gate passed 20/20 under independent `Gemini Pro` semantic judgment.
- Wave G usefulness/safety/correctness/relevance/boundary/hallucination scores are all 1.0000; critical safety failures=0.
- The selected local chat model is now `qwen3.5:9b`, chosen after anonymous pairwise judgment against `gemma3:4b` (13 wins, 3 losses, 4 ties).
- Built `case_packs/v0_251_independent_chat_golden_blind_set_boundary_adversarial_cases.json`.
- Standalone validation: 18/18 passed, including candidate-audit checks.
- Promoted the pack into `cases/v0_251_independent_chat_golden_blind_set_boundary_adversarial_cases.json`.
- Core eval: 2228/2228 passed.
- State dataset: 2228 records, errors=0, warnings=0.
- State encoder candidate: exact_match=1.000, B_sigma exact_match=1.000, micro_f1=1.000.
- Admission gate: passed=True, observed={'exact_match': 1.0, 'micro_f1': 1.0, 'critical_false_negatives': 0}.
- Shadow replacement boundary: ledger_events=0, replacement_boundary_passed=True.
- Candidate-assisted mode: override_events=0, drift_present=False, rule_replacement_allowed=false.
- Holdout no-retrain ledger events: 0 on `v251_`.
- Required candidate-output gate: 1975 cases, clean=True, gated PSM unsafe/risky=0.
- Fault injection events: 7206.
- Controller rescue count: 1975.
- Candidate taxonomy: rows=5940, ledger_events=17864, invariants_passed=True.
- Candidate regression fixtures: coverage_passed=True, fixtures=6.
- Taxonomy delta: changed_groups=47, unexpected_regression=False.
- Project status: `project_status_out/psm_v0.251_project_status.json`.
- Regression: passed=True with explicit taxonomy-expansion allowance.
- At completion, the assigned next stage is `PSM_V0.252`.

## Next Stage

`PSM V0.252`

Bring the local chat experience to a stable internal alpha:

- add explicit generating, cancel, timeout, retry, and failure-recovery states;
- stream or progressively reveal the answer so the selected 9B model does not leave the UI silent;
- keep debug evidence hidden from the main conversation;
- add desktop/mobile, keyboard, accessibility, duplicate-message, and overflow regression coverage;
- rebuild and verify both the local server and Docker runtime.

- Blocked: false.
- Requires user input: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.251_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
