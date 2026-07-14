# PSM Current Status

## Current Version

`PSM V0.257`

The current project status is `psm_v0.257`. V0.257 promotes the first source-isolated trainable shadow state-encoder baseline while retaining `psm_v0.251` as the formal 2228-record core evidence source, the V0.255 stable internal local chat Alpha decision, and the V0.256 annotation contract.

## Latest Completed Result

- The V0.257 benchmark contains 42 synthetic non-private records: 14 train, 14 validation, and 14 test, with distinct source families and clean family/source/time isolation.
- A trainable multinomial Naive Bayes model estimates seven separate heads for Q, Omega, phi, Delta sigma, Pi, eta, and B_sigma projections.
- Candidate features include request text and public evidence status only; source identity, source time, split, annotation, consensus, and judge fields are excluded.
- The initial run was rejected at 0.142857 validation/test exact match with three critical false negatives on each protected split; the failure remains recorded.
- The repair corrected out-of-vocabulary likelihood handling and medical synonym coverage without adding validation or test rows to training and without changing labels or splits.
- Final candidate validation exact match: 0.928571. Test exact match: 1.0. Critical false negatives: 0/0.
- Transparent-rule validation/test exact match remains 1.0/1.0, so deterministic gating remains the controller and the candidate remains shadow-only.
- Protected backflow: 0. External user trial, professional authority, rule replacement, and external release authority remain closed.

## Next Stage

`PSM V0.258`

Calibrate and expand the shadow state encoder:

- add new source families without crossing the existing family/source/time boundary;
- calibrate confidence separately for all seven heads;
- add low-confidence abstention and unresolved-disagreement evaluation;
- report calibration error, coverage, critical false negatives, and cross-family stability;
- keep validation, test, blind, and judge-only feedback out of training;
- keep the candidate shadow-only and retain the deterministic rule controller.

- Blocked: false.
- Requires user input: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.257_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Shadow encoder checkpoint: `runtime/v0_257_shadow_encoder_checkpoint.json`.
- Shadow encoder gate: `runtime/v0_257_shadow_encoder_gate.json`.
- Shadow encoder metrics: `runtime/v0_257_shadow_encoder_metrics.json`.
- Shadow encoder model: `runtime/v0_257_shadow_encoder_model.json`.
- Initial rejection: `runtime/v0_257_shadow_encoder_initial_rejection.json`.
- Residual risks: `runtime/v0_257_shadow_encoder_residual_risks.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
