# PSM V0.270 Core Workspace

The current promoted project status is `psm_v0.270`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records. V0.270 adds source-isolated multi-turn evidence without changing the formal core.

## Latest Result

- V0.269 passes 21/21 repeated task runs, zero provider/deterministic drift, local p50 23 ms and p95 16.771 s, plus recovery/browser/Docker gates.
- V0.270 passes 12/12 multi-turn cases after retaining five initial failures, two domain-label errata, and one evaluator-gap record.
- Assistant-history contamination and stale-constraint violations are zero.
- 189 tests, desktop/mobile browser regression, and host/Docker parity pass after local V0.271 repairs.
- V0.271 is not promoted: external `gpt-5.4` review failed M07/M08. Both are repaired locally, but the USD 20/20 monthly budget blocks rejudging.

## Run

```bash
make check
make serve
make multiturn-v270-eval
make browser-regression-v270-multiturn
make multiturn-v270-docker
make prepare-v271
make repair-v271-local
```

The normal chat is `http://127.0.0.1:8765/`. The historical operator page at `/trial-enrollment` displays the completed V0.264 record and collects no feedback.

## Boundaries

- V0.270 evidence is internally authored and synthetic; it is not human or independent blind evidence.
- The failed V0.271 external review and successful local repairs are distinct evidence states.
- Evaluation rows cannot become training truth or grant rule-replacement authority.
- Public service, production readiness, professional action, privacy-compliance claims, and external release authority remain closed.

## Recovery

- `CURRENT_STATUS.md` is the human recovery point.
- `project_status_out/psm_v0.270_project_status.json` is the promoted machine status.
- `runtime/v0_271_external_multiturn_checkpoint.json` records the active rejudge budget blocker.
- `roadmap_out/PSM_V0.270_to_V0.271_External_Multiturn_Roadmap.md` is the active roadmap.
