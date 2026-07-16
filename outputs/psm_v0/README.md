# PSM V0.274 Core Workspace

The current promoted project status is `psm_v0.274`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records. V0.274 adds a user-authoritative open-context state capsule without changing the formal core.

## Latest Result

- V0.269 passes 21/21 repeated task runs, zero provider/deterministic drift, local p50 23 ms and p95 16.771 s, plus recovery/browser/Docker gates.
- V0.270 passes 12/12 multi-turn cases after retaining five initial failures, two domain-label errata, and one evaluator-gap record.
- Assistant-history contamination and stale-constraint violations are zero.
- 210 tests, desktop/mobile browser regression, and host/Docker parity pass.
- V0.271 retains the original M07/M08 external failure, then passes a user-approved 12/12 `gpt-5.4` rejudge after local repair, with zero critical findings and no API retry after the retained runner display failure.
- V0.274 retains a 0/10 first run, then passes 10/10 unseen open-context conversations with zero stale-state violations and no missing state capsules; browser and Docker boundaries pass.
- V0.275 retains its first independent FAIL on O01, O02, and O10 after one authorized call and 9,401 tokens. Local repairs change only those three answers and pass 10/10; no external rejudge is authorized, and the USD 32/32 synthetic API ledger is closed.

## Run

```bash
make check
make serve
make multiturn-v270-eval
make browser-regression-v270-multiturn
make multiturn-v270-docker
make prepare-v271
make repair-v271-local
make authorize-v271-rejudge
make rejudge-v271-openai
make finalize-v271
make promote-v271
make long-context-v272-eval
make browser-regression-v272-long-context
make long-context-v272-docker
make promote-v272
make prepare-v273
make authorize-v275
make judge-v275-openai
make repair-v275-local
```

The normal chat is `http://127.0.0.1:8765/`. The historical operator page at `/trial-enrollment` displays the completed V0.264 record and collects no feedback.

## Boundaries

- V0.274 evidence is internally authored and synthetic; it is not human evidence.
- The failed V0.271 review, local repairs, and passing external rejudge remain distinct evidence states.
- Evaluation rows cannot become training truth or grant rule-replacement authority.
- Public service, production readiness, professional action, privacy-compliance claims, and external release authority remain closed.

## Recovery

- `CURRENT_STATUS.md` is the human recovery point.
- `project_status_out/psm_v0.274_project_status.json` is the promoted machine status.
- `runtime/v0_275_external_open_context_checkpoint.json` records the failed first review, local repair, and active external-rejudge budget blocker.
- `roadmap_out/PSM_V0.274_to_V0.275_External_Open_Context_Roadmap.md` is the active roadmap.
