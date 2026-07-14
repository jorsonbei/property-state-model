# PSM Current Status

## Current Version

`PSM V0.247`

The current project status is `psm_v0.247`. It promoted `chat_alpha_integration_data_lifecycle_boundary_adversarial` into the formal core.

## Verified Result

- Formal cases: 2192.
- Core eval: 2192/2192 passed.
- Required/fault candidate gate: 1939 cases.
- Required gated PSM unsafe/risky: 0.
- Fault injection events: 7092.
- Controller rescue count: 1939.
- State dataset errors/warnings: 0/0.
- Deterministic regression: passed.
- Rule replacement allowed: false.
- External user trial allowed: false.

## Authoritative Artifacts

- Machine status: `project_status_out/psm_v0.247_project_status.json`.
- Regression: `regression_out/psm_v0.247_regression_check.json`.
- Formal case pack: `cases/v0_247_chat_alpha_integration_data_lifecycle_boundary_adversarial_cases.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

## Next Stage

`PSM V0.248`

Before refreshing optional external/controller evidence for `v247_`, harden the recovery/tooling contract, define the V0.249 family, unify fixture paths, and verify the local version-control baseline.

- Blocked: false.
- Requires user input: false.

Historical recursive status content was preserved locally under `status_history/` and is not part of the public repository.
