# PSM Current Status

## Current Version

`PSM V0.256`

The current project status is `psm_v0.256`. V0.256 promotes the source-isolated property-state annotation and dataset contract while retaining `psm_v0.251` as the formal 2228-record core evidence source and the V0.255 stable internal local chat Alpha decision.

## Latest Completed Result

- A frozen contract now defines Q, Omega, phi, Delta sigma, Pi, eta, and B_sigma targets, required evidence fields, and unknown-retention policy.
- Eight synthetic non-private records carry 16 independent annotations across train, validation, and test source families.
- Three intentional target disagreements remain `unresolved`; none is flattened into training truth.
- Source overlap: 0. Family overlap: 0. Exact-content overlap: 0. Cross-split near duplicates: 0.
- Candidate-input target/judge leakage: 0. Validation/test backflow into training: 0.
- Three resolved train records are exportable only as a shadow-training preview; training has not started.
- A synthetic-only external review package is prepared under user authorization; submission is pending because no external API credential is configured.
- V0.255 internal-chat evidence remains retained: blind Wave G 20/20, current scenarios 13/13, critical fact hallucinations 0, critical safety false negatives 0.
- External user trial, professional authority, rule replacement, and external release authority remain closed.

## Next Stage

`PSM V0.257`

Build the first source-isolated shadow state-encoder baseline:

- train only from resolved V0.256 training annotations;
- compare majority, transparent-rule, and trainable candidates per state target;
- report train, validation, and test metrics separately;
- keep validation, test, blind, and judge-only artifacts out of training;
- require critical safety false negatives to remain non-increasing;
- keep every candidate shadow-only and retain the deterministic rule controller.

- Blocked: false.
- Requires user input: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.256_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Annotation contract: `benchmarks/v0_256_state_annotation_contract.json`.
- Annotation checkpoint: `runtime/v0_256_annotation_contract_checkpoint.json`.
- Annotation gate: `runtime/v0_256_annotation_contract_gate.json`.
- Source-isolation report: `runtime/v0_256_source_isolation_report.json`.
- External review package: `runtime/v0_256_external_contract_review_package.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
