# PSM Current Status

## Current Version

`PSM V0.263`

V0.263 promotes the completed three-person supervised enrollment gate. The formal 2228-record evidence core remains `PSM V0.251`; V0.263 adds real operator-attested enrollment and content-free local trial evidence without changing the formal core.

## Latest Completed Result

- P01-P03 each completed operator adulthood verification, notice display, acknowledgment, explicit consent, and supervised session enablement in strict timestamp order.
- The three-person cohort gate and all three private invitation access checks pass.
- At promotion, six allowed low-risk session events had been recorded for one pseudonymous participant; raw prompts and answers were not retained and participant content was not sent to an external API.
- Desktop and mobile completion regression pass with all invitation codes masked and no participant messages sent by the test.
- Docker contains no private enrollment state, cannot access operator cards or trial chat, and remains bound to `127.0.0.1:8766`.
- Git-tracked files contain zero private invitation, binding, or audit-secret values.
- Public service, privacy-compliance claims, production readiness, training on trial data, rule replacement, professional authority, and external release authority remain closed.

## Next Stage

`PSM V0.264`

Run the bounded three-person supervised pilot:

- require at least three allowed low-risk general turns from each of P01-P03;
- keep the operator physically present and prohibit remote or unsupervised use;
- retain only content-free operational metadata for seven days;
- collect no direct identity, raw prompt, or raw answer;
- stop all sessions without automatic resume on any privacy, consent, supervision, prohibited-data, or provider-boundary event.

Current frozen checkpoint: P01 is complete at 3/3 credited turns; P02 is 0/3; P03 is 0/3. This stage requires real participant action and cannot be completed by code.

Operator URL: `http://127.0.0.1:8765/trial-enrollment`.

- Blocked: true.
- Requires user input: true.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.263_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- V0.263 completion gate: `runtime/v0_263_completed_enrollment_gate.json`.
- V0.263 completed browser evidence: `runtime/v0_263_completed_enrollment_browser_regression/report.json`.
- V0.263 completed Docker boundary: `runtime/v0_263_completed_enrollment_docker_boundary.json`.
- V0.263 promotion manifest: `runtime/v0_263_enrollment_promotion_manifest.json`.
- V0.264 contract: `benchmarks/v0_264_supervised_pilot_contract.json`.
- V0.264 checkpoint: `runtime/v0_264_supervised_pilot_checkpoint.json`.
- Current execution roadmap: `roadmap_out/PSM_Supervised_Pilot_Roadmap_V0.263_to_V0.264.md`.

Version history remains in independent snapshots under `status_history/`; it is not embedded recursively here.
