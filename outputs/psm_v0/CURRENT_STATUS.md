# PSM Current Status

## Current Version

`PSM V0.292`

V0.292 is promoted. The deterministic 2228-record formal evidence source remains `PSM V0.251`; V0.283-V0.292 add continuity recovery, independent semantic review, runtime/browser parity, latency measurement, and server-cancel evidence without changing that formal core.

## Latest Results

- V0.283 retains a 0/5 lifecycle baseline and finishes 5/5 across active, reset, reload, expired, and restarted states. Host, Docker, desktop, and mobile checks pass; archived-fact fabrication is 0.
- V0.284 passes a 5/5 independent `gpt-5.4` semantic review of lifecycle recovery answers.
- V0.285 retains a 5/8 adversarial baseline, closes old-memory resurrection, and finishes 8/8. Cross-session leaks are 0 across 32 concurrent sessions; expiry tombstones are capped at 128 and store hashes only.
- V0.286 retains a 4/16 natural-reference baseline and finishes 16/16, including 12 Chinese/Traditional-Chinese/English prior references and four explicit new-task controls. All 48 loss-state answer checks pass with zero archived-fact fabrication.
- V0.287 passes an independent 16/16 `gpt-5.4` review with no failed items or critical findings.
- V0.288 passes 16/16 on both host and Docker, including authentic server-owned expiry eviction. Synthetic raw-text sentinel disk writes are 0; the retained first runtime attempt documents the invalid client-expiry injection gap.
- V0.289 passes real Chromium desktop/mobile recovery, new-task, continuity-label, layout, and console gates.
- V0.290 records deterministic recovery/identity P95 below 38 ms. Normal local-model generation succeeds 6/6 with fallback 0; host P50/P95 is 16.4/16.7 seconds and Docker P50/P95 is 13.4/16.7 seconds.
- V0.291 passes real-browser staged progress, cancellation, prompt preservation, retry, and single-turn integrity. Observed client cancellation is 37 ms. Server-side inference cancellation and network streaming are explicitly not claimed.
- V0.292 passes 6/6 active server cancellations across host and Docker. Maximum observed chat-worker stop time is 38.49/276.25 ms; both runtimes complete a normal Ollama retry afterward. Desktop/mobile server acknowledgements, no-partial-answer, single-turn retry, no-overflow, zero-console-error, 249/249 regression, and zero disk-sentinel gates pass.

## Token Authority

- User-authorized ceiling: 1,000,000 cumulative tokens for synthetic external judging.
- Observed usage: 157,268 tokens.
- Remaining authority: 842,732 tokens.
- Per-call approval required within this ceiling: false.
- Private data, participant content, user documents, training feedback, and external release are outside this authority.

## Memory And Release Boundary

- Browser/server visible message window: 120 messages.
- Rolling user-state maximum: 20 statements.
- Session memory: process memory only, maximum 64 sessions, 30-minute idle expiry.
- Expiry tombstones: maximum 128, SHA-256 session hashes only, one-hour TTL.
- User-statement and raw-conversation disk persistence: false.
- Client continuity events: active, reset, reload. Expired and restarted states remain server-owned.
- Page reset, reload, server restart, and expiry intentionally discard rolling memory and require restatement for prior-reference questions.
- Client cancel closes the server-owned Ollama HTTP connection and stops the chat worker. Direct model-kernel/GPU stop instrumentation remains unclaimed.
- Raw Ollama chunks stay server-buffered until complete-answer review; network token streaming is not enabled.
- Human validation, public service, production readiness, rule replacement, professional authority, and external release authority: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.292_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- V0.283 restart recovery: `runtime/v0_283_restart_recovery_gate.json`, `runtime/v0_283_controlled_restart_boundary.json`, `runtime/v0_283_restart_recovery_browser_regression/report.json`.
- V0.284 external review: `runtime/v0_284_openai_external_restart_recovery_judge.json`, `runtime/v0_284_external_restart_recovery_gate.json`.
- V0.285 lifecycle integrity: `runtime/v0_285_lifecycle_signal_integrity_report.json`, `runtime/v0_285_host_docker_integrity_boundary.json`.
- V0.286 natural references: `benchmarks/v0_286_natural_recovery_reference_contract.json`, `runtime/v0_286_natural_recovery_reference_report.json`.
- V0.287 external review: `runtime/v0_287_openai_external_natural_recovery_judge.json`, `runtime/v0_287_external_natural_recovery_gate.json`.
- V0.288 runtime parity: `runtime/v0_288_host_docker_natural_recovery_boundary.json`, `runtime/v0_288_host_docker_attempt_1_evaluator_gap.json`.
- V0.289 browser recovery: `runtime/v0_289_natural_recovery_browser_regression/report.json`.
- V0.290 latency: `benchmarks/v0_290_latency_budget_contract.json`, `runtime/v0_290_latency_budget_report.json`.
- V0.291 cancel/retry: `runtime/v0_291_cancel_retry_browser_regression/report.json`, `runtime/v0_291_cancel_retry_checkpoint.json`.
- V0.292 server cancel: `benchmarks/v0_292_server_cancel_contract.json`, `runtime/v0_292_server_cancel_runtime_report.json`, `runtime/v0_292_server_cancel_browser_regression/report.json`.

## Next Stage

`PSM V0.293` freezes and validates concurrency capacity, backpressure, duplicate request IDs, cancellation storms, and disconnect races. It requires no user input and grants no external release authority.

Version history remains in independent snapshots under `status_history/`; it is not embedded recursively here.
