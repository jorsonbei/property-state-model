# PSM Current Status

## Current Version

`PSM V0.282`

V0.282 is promoted. The deterministic 2228-record formal evidence source remains `PSM V0.251`; V0.282 adds bounded cross-window state continuity and real-browser lifecycle evidence without changing that formal core.

## Latest Results

- V0.275 retains its O01/O02/O10 and O09 external failures, then passes an independent 10/10 third review after local repair.
- V0.276 retains a 0/10 truncation baseline and finishes 10/10 across five long-horizon state families.
- V0.277 independently reviews the V0.276 answers and passes 10/10.
- V0.278 passes 10/10 at 81 and 119 messages; stale-state, compression, and capsule-recovery failures are 0, with 30 ms P95.
- V0.279 independently reviews the 81/119-message answers and passes 10/10.
- V0.280 retains a 4/4 failure after early state exits the 120-message window, then passes 4/4 with rolling state handoff. Host and Docker recover the archived fact while the visible window remains bounded to 120.
- V0.281 passes 11 session isolation, expiry, replay, and capacity checks, then passes a 4/4 independent external review.
- V0.282 passes real Playwright desktop/mobile lifecycle regression: the visible cross-window answer is correct, reset/reload rotate sessions, overflow is 0, and console errors are 0.

## Token Authority

- User-authorized ceiling: 1,000,000 cumulative tokens for synthetic external judging.
- Observed usage: 150,416 tokens.
- Remaining authority: 849,584 tokens.
- Per-call approval required within this ceiling: false.
- Private data, participant content, user documents, training feedback, and external release are outside this authority.

## Memory And Release Boundary

- Browser/server message window: 120 messages.
- Rolling user-state maximum: 20 statements.
- Session memory: process memory only, maximum 64 sessions, 30-minute idle expiry.
- User-statement disk persistence: false.
- Assistant history cannot override user facts; explicit topic switches clear old-topic state.
- Page reset, page reload, server restart, and session expiry intentionally discard rolling memory.
- Human validation, public service, production readiness, rule replacement, professional authority, and external release authority: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.282_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- V0.276 contract/report/gate: `benchmarks/v0_276_long_horizon_state_compression_contract.json`, `runtime/v0_276_long_horizon_state_compression_report.json`, `runtime/v0_276_long_horizon_state_compression_gate.json`.
- V0.277 package/judge/gate: `runtime/v0_277_external_state_compression_review_package.json`, `runtime/v0_277_openai_external_state_compression_judge.json`, `runtime/v0_277_external_state_compression_gate.json`.
- V0.278 stress contract/report/Docker: `benchmarks/v0_278_incremental_long_horizon_stress_contract.json`, `runtime/v0_278_incremental_long_horizon_stress_report.json`, `runtime/v0_278_incremental_long_horizon_stress_docker_boundary.json`.
- V0.279 package/judge/gate: `runtime/v0_279_external_incremental_stress_review_package.json`, `runtime/v0_279_openai_external_incremental_stress_judge.json`, `runtime/v0_279_external_incremental_stress_gate.json`.
- V0.280 contract/baseline/report/Docker: `benchmarks/v0_280_rolling_state_handoff_contract.json`, `runtime/v0_280_window_truncation_initial_failure_ledger.json`, `runtime/v0_280_rolling_state_handoff_report.json`, `runtime/v0_280_rolling_state_handoff_docker_boundary.json`.
- V0.281 isolation/external review: `runtime/v0_281_rolling_state_isolation_gate.json`, `runtime/v0_281_external_rolling_state_review_package.json`, `runtime/v0_281_openai_external_rolling_state_judge.json`, `runtime/v0_281_external_rolling_state_gate.json`.
- V0.282 browser report: `runtime/v0_282_rolling_state_browser_regression/report.json`.
- Current roadmap: `roadmap_out/PSM_V0.282_to_V0.283_Restart_Recovery_Roadmap.md`.

Version history remains in independent snapshots under `status_history/`; it is not embedded recursively here.
