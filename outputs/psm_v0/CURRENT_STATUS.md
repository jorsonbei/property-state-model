# PSM Current Status

## Current Version

`PSM V0.260`

The current project status is `psm_v0.260`. V0.260 completes the internal trial readiness review while retaining `psm_v0.251` as the formal 2228-record core evidence source and preserving all V0.255-V0.259 chat, annotation, shadow, calibration, and Sigma+ gates.

## Latest Completed Result

- The frozen machine decision is `internal_trial_ready` for local single-user internal use only.
- Formal core 2228/2228, independent blind semantic gate 20/20, and internal Alpha scenarios 13/13 remain passing.
- Current project verification passes 114 tests and parses 162 Python sources.
- Critical fact hallucinations and critical safety false negatives are both 0.
- The selected local model remains `qwen3.5:9b`, with failure rate 0 and p95 latency 22949 ms below the 60000 ms server timeout.
- Sigma+ delivery remains 15/15 with 22 strong claims and complete provenance-or-downgrade coverage.
- Seventeen residual risks remain explicit: 12 open/not-built and 5 bounded/accepted only within the local internal scope.
- The synthetic non-private V0.256 external contract review is authorized, but it has not been submitted because no external API credential is configured.
- External users, privacy-compliance claims, public service, professional authority, shadow output control, rule replacement, and external release authority remain closed.

## Next Stage

`PSM V0.261`

Define and authorize the post-internal external-validation lane:

- decide whether to prepare an external-user trial and define its participant scope;
- define data handling, privacy, retention, and deletion requirements;
- choose deployment mode and budget;
- configure a usable external-model API credential if the authorized synthetic contract judge should be submitted;
- do not upload data or open external use before those user-owned decisions are supplied.

- Blocked: true.
- Requires user input: true.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.260_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Internal readiness checkpoint: `runtime/v0_260_internal_readiness_checkpoint.json`.
- Internal readiness review: `runtime/v0_260_internal_readiness_review.json`.
- Evidence manifest: `runtime/v0_260_internal_readiness_evidence_manifest.json`.
- Residual risks: `runtime/v0_260_internal_readiness_residual_risks.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
