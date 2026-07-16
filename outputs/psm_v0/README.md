# PSM V0.291 Core Workspace

The current promoted project status is `psm_v0.291`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records. V0.283-V0.291 add continuity recovery, independent review, host/Docker/browser parity, latency budgets, and cancel/retry evidence without changing the formal core.

## Latest Result

- Lifecycle recovery moved from a retained 0/5 baseline to 5/5; same-session resurrection moved from 5/8 to 8/8.
- Natural prior-reference detection moved from 4/16 to 16/16, with 48 loss-state answer checks and zero archived-fact fabrication.
- Independent V0.284 and V0.287 `gpt-5.4` reviews pass 5/5 and 16/16. Synthetic external-judge usage is 157,268 / 1,000,000 authorized tokens.
- Host and Docker each pass 16/16 natural-reference/new-task runtime cases; raw-text sentinel disk writes are 0.
- Desktop and mobile Chromium recovery/cancel/retry regressions pass with zero overflow or console errors.
- Deterministic P95 is below 38 ms. Normal local-model generation P95 is about 16.7 seconds with 6/6 success and zero fallback.
- Client cancellation is observed at 37 ms and preserves one retryable user turn. Server inference cancellation and network streaming are not claimed.

## Run

```bash
make check
make serve
make recovery-v286-eval
make runtime-v288-parity
make browser-v289-recovery
make latency-v290-eval
make browser-v291-cancel
```

The normal chat is `http://127.0.0.1:8765/`. Docker chat is `http://127.0.0.1:8766/`.

## Boundaries

- The browser retains at most 120 visible messages.
- Rolling state retains at most 20 user statements in process memory, expires after 30 idle minutes, and is capped at 64 sessions.
- Expiry tombstones are hash-only, capped at 128, and expire after one hour.
- User statements and raw conversations are not persisted to disk; reset, reload, server restart, and expiry discard rolling memory.
- Browser cancel currently stops client waiting only; it does not prove server-side inference cancellation.
- Human validation, evaluation-to-training backflow, public service, professional action, rule replacement, and external release remain closed.

## Recovery

- `CURRENT_STATUS.md` is the human recovery point.
- `project_status_out/psm_v0.291_project_status.json` is the promoted machine status.
- `runtime/current_runtime_snapshot.json` is the Docker/public runtime snapshot.
- `runtime/v0_291_cancel_retry_checkpoint.json` opens the V0.292 server-cancel/streaming protocol stage.
