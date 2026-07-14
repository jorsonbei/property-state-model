# PSM Current Status

## Current Version

`PSM V0.258`

The current project status is `psm_v0.258`. V0.258 promotes source-isolated per-head confidence calibration and fail-closed abstention while retaining `psm_v0.251` as the formal 2228-record core evidence source, V0.255 stable internal local chat, the V0.256 annotation contract, and the frozen V0.257 trainable shadow baseline.

## Latest Completed Result

- The V0.257 model and training dataset are frozen by SHA-256; V0.258 changes neither base weights nor base training rows.
- V0.258 adds 35 synthetic non-private records: 14 calibration, 14 evaluation, and 7 unresolved. Every purpose uses a distinct source family and time boundary.
- Source-family, source-id, exact-content, and near-duplicate overlap are all 0.
- All seven heads receive temperature calibration and a calibration-only confidence floor.
- New-source evaluation average coverage is 0.959184 and minimum selective accuracy is 0.928571.
- Four low-confidence evaluation targets abstain. Accepted critical false negatives are 0.
- Seven unresolved targets all fail closed through the consensus contract and never become forced training truth.
- The model itself detected 0/7 unresolved cases through low confidence. This remains an open limitation; consensus and deterministic rules retain authority.
- Protected feedback to base training is 0. External user trial, professional authority, rule replacement, and external release authority remain closed.

## Next Stage

`PSM V0.259`

Build the Sigma+ traceable delivery contract:

- join natural answers, property state, provenance, tool results, failures, and statement levels in one delivery packet;
- require every strong claim to have evidence provenance or an explicit downgrade;
- route calibrated low-confidence and unresolved targets back to deterministic rules;
- keep internal state, thresholds, and debug terms out of ordinary chat;
- audit API, desktop, mobile, and Docker behavior without granting the shadow candidate release authority.

- Blocked: false.
- Requires user input: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.258_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Calibrated shadow checkpoint: `runtime/v0_258_calibrated_shadow_checkpoint.json`.
- Calibrated shadow gate: `runtime/v0_258_calibrated_shadow_gate.json`.
- Calibration report: `runtime/v0_258_confidence_calibration.json`.
- Calibrated shadow metrics: `runtime/v0_258_calibrated_shadow_metrics.json`.
- Initial rejection: `runtime/v0_258_calibrated_shadow_initial_rejection.json`.
- Residual risks: `runtime/v0_258_calibrated_shadow_residual_risks.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
