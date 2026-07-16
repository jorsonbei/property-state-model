# PSM V0.282 Core Workspace

The current promoted project status is `psm_v0.282`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records. V0.282 adds bounded rolling state continuity and browser lifecycle evidence without changing the formal core.

## Latest Result

- V0.276 moves long-horizon state recovery from a retained 0/10 baseline to 10/10.
- V0.277 and V0.279 independently pass 10/10 external semantic reviews.
- V0.278 passes 10/10 at 81/119 messages with 30 ms P95 and zero stale-state or capsule-recovery failures.
- V0.280 moves cross-window recovery from a retained 0/4 truncation baseline to 4/4, including host/Docker verification.
- V0.281 passes 11/11 session isolation checks and a 4/4 external rolling-state review.
- V0.282 passes real desktop/mobile browser lifecycle regression with the correct visible answer, rotating reset/reload sessions, no overflow, and no console errors.
- Synthetic external-judge usage is 150,416 / 1,000,000 authorized tokens.

## Run

```bash
make check
make serve
make rolling-v280-eval
make rolling-v280-docker
make isolation-v281-eval
make browser-v282-rolling
```

The normal chat is `http://127.0.0.1:8765/`. Docker chat is `http://127.0.0.1:8766/`.

## Boundaries

- The browser retains at most 120 messages.
- Rolling state retains at most 20 user statements in process memory, expires after 30 idle minutes, and is capped at 64 sessions.
- User statements are not persisted to disk; reset, reload, server restart, and expiry discard rolling memory.
- Human validation, evaluation-to-training backflow, public service, professional action, rule replacement, and external release remain closed.

## Recovery

- `CURRENT_STATUS.md` is the human recovery point.
- `project_status_out/psm_v0.282_project_status.json` is the promoted machine status.
- `runtime/v0_282_rolling_state_browser_regression/report.json` is the latest browser gate.
- `roadmap_out/PSM_V0.282_to_V0.283_Restart_Recovery_Roadmap.md` is the active roadmap.
