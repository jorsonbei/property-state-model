# PSM Current Status

## Current Version

`PSM V0.264`

V0.264 promotes the completed three-person supervised pilot. The formal 2228-record evidence core remains `PSM V0.251`; V0.264 adds bounded real-participant coverage evidence without changing the formal core.

## Latest Completed Result

- P01-P03 each completed at least three operator-supervised low-risk turns: credited coverage is 3/3, 3/3, and 3/3.
- The private audit state contains 20 allowed low-risk content-free events, zero rejected events, zero persisted raw prompts or answers, and zero participant-content external API calls.
- The V0.264 evaluator, completed desktop/mobile browser regression, Git secret scan, private file-permission check, and Docker boundary all pass.
- V0.264 is promoted by `runtime/v0_264_supervised_pilot_promotion_manifest.json`.
- Public service, privacy-compliance claims, production readiness, training on trial data, rule replacement, professional authority, and external release authority remain closed.

## Next Stage

`PSM V0.265`

The engineering surface is complete and verified. For each new supervised low-risk answer, the participant can now submit exactly four fixed fields: helpfulness, clarity, state alignment, and issue category. There is no free-text feedback field.

Current frozen checkpoint:

- P01 structured feedback: 0/3.
- P02 structured feedback: 0/3.
- P03 structured feedback: 0/3.
- Quality thresholds are not evaluated until all three participants reach 3/3.

Each participant must ask three new ordinary low-risk questions while the operator is physically present and submit the fixed evaluation under each answer. Do not enter names, contact details, identity documents, secrets, medical or legal requests, trading decisions, or other private data.

Operator URL: `http://127.0.0.1:8765/trial-enrollment`.

- Blocked: true.
- Requires user input: true.

## V0.265 Gate

- Coverage: three rated turns per participant.
- Median helpfulness: at least 4/5.
- Median clarity: at least 4/5.
- `yes` or `partial` state-alignment ratio: at least 2/3.
- `no` state-alignment events: zero.
- Possible factual-error or unsafe/inappropriate events: zero.
- Feedback remains a subjective pilot signal only and cannot authorize training or public release.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.264_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- V0.264 gate: `runtime/v0_264_supervised_pilot_gate.json`.
- V0.264 browser evidence: `runtime/v0_264_supervised_pilot_browser_regression/report.json`.
- V0.264 Docker boundary: `runtime/v0_264_supervised_pilot_docker_boundary.json`.
- V0.264 promotion manifest: `runtime/v0_264_supervised_pilot_promotion_manifest.json`.
- V0.265 contract: `benchmarks/v0_265_structured_feedback_contract.json`.
- V0.265 checkpoint: `runtime/v0_265_structured_feedback_checkpoint.json`.
- V0.265 browser evidence: `runtime/v0_265_structured_feedback_browser_regression/report.json`.
- V0.265 Docker boundary: `runtime/v0_265_structured_feedback_docker_boundary.json`.
- Current execution roadmap: `roadmap_out/PSM_Structured_Feedback_Roadmap_V0.264_to_V0.265.md`.

Version history remains in independent snapshots under `status_history/`; it is not embedded recursively here.
