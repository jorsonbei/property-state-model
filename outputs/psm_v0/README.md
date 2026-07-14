# PSM V0.251 Core Workspace

The current project status is `psm_v0.251`. It promoted `independent_chat_golden_blind_set_boundary_adversarial` into the formal core, bringing the formal dataset to 2228 records. Required/fault candidate gating covers 1975 cases with gated PSM unsafe/risky at 0.

## Latest Result

- Frozen Wave G independent semantic gate: passed 20/20 with usefulness and safety both 1.0000 and no critical safety failure.
- Selected local model: `qwen3.5:9b`; anonymous external comparison versus `gemma3:4b` was 13 wins, 3 losses, and 4 ties.
- V0.251 promoted expansion family: `independent_chat_golden_blind_set_boundary_adversarial`.
- V0.251 core eval: 2228/2228 passed.
- V0.251 candidate taxonomy: rows=5940, ledger_events=17864, invariants passed.
- V0.251 deterministic regression: passed=True.
- Next stage: V0.252 product interaction and browser regression.

## Run

From the repository root:

```bash
make check
make serve
```

## Boundaries

- Internal local chat demo only.
- Ordinary and raw PSM outputs are not release candidates.
- External user trial remains closed.
- Rule replacement remains disabled.

## Recovery

- `CURRENT_STATUS.md` is the current human recovery point.
- `project_status_out/psm_v0.251_project_status.json` is the machine status.
- Historical generated evidence remains local and is excluded from Git.
