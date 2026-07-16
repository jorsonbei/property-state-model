# PSM V0.292 Core Workspace

The current promoted project status is `psm_v0.292`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records. V0.283-V0.292 add continuity recovery, independent review, host/Docker/browser parity, latency budgets, and server-cancel evidence without changing the formal core.

## Latest Result

- Lifecycle recovery moved from a retained 0/5 baseline to 5/5; same-session resurrection moved from 5/8 to 8/8.
- Natural prior-reference detection moved from 4/16 to 16/16, with 48 loss-state answer checks and zero archived-fact fabrication.
- Independent V0.284 and V0.287 `gpt-5.4` reviews pass 5/5 and 16/16. Synthetic external-judge usage is 157,268 / 1,000,000 authorized tokens.
- Host and Docker each pass 16/16 natural-reference/new-task runtime cases; raw-text sentinel disk writes are 0.
- Desktop and mobile Chromium recovery/cancel/retry regressions pass with zero overflow or console errors.
- Deterministic P95 is below 38 ms. Normal local-model generation P95 is about 16.7 seconds with 6/6 success and zero fallback.
- Host and Docker each cancel 3/3 active server requests. Observed maximum chat-worker stop time is 38.49 ms / 276.25 ms, and retry succeeds on both runtimes.
- Desktop/mobile Chromium confirms active server cancellation, no partial assistant answer, single-turn retry, zero overflow, and zero console errors. Network token streaming is not claimed.

## Run

```bash
make check
make serve
make recovery-v286-eval
make runtime-v288-parity
make browser-v289-recovery
make latency-v290-eval
make browser-v291-cancel
make server-cancel-v292-eval
make browser-v292-cancel
```

The normal chat is `http://127.0.0.1:8765/`. Docker chat is `http://127.0.0.1:8766/`.

## Boundaries

- The browser retains at most 120 visible messages.
- Rolling state retains at most 20 user statements in process memory, expires after 30 idle minutes, and is capped at 64 sessions.
- Expiry tombstones are hash-only, capped at 128, and expire after one hour.
- User statements and raw conversations are not persisted to disk; reset, reload, server restart, and expiry discard rolling memory.
- Browser cancel now closes the server-owned Ollama HTTP connection and stops the chat worker; direct model-kernel/GPU stop instrumentation is not claimed.
- Ollama chunks remain server-buffered until the complete candidate passes answer gates; raw network token streaming is not enabled.
- Human validation, evaluation-to-training backflow, public service, professional action, rule replacement, and external release remain closed.

## Recovery

- `CURRENT_STATUS.md` is the human recovery point.
- `project_status_out/psm_v0.292_project_status.json` is the promoted machine status.
- `runtime/current_runtime_snapshot.json` is the Docker/public runtime snapshot.
- `runtime/v0_292_server_cancel_checkpoint.json` opens the V0.293 concurrency/backpressure stage.
