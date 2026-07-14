# PSM V0.249 Core Workspace

The current project status is `psm_v0.249`. It promoted `chat_quality_intent_grounding_boundary_adversarial` into the formal core, bringing the formal dataset to 2210 records. Required/fault candidate gating covers 1957 cases with gated PSM unsafe/risky at 0.

## Latest Result

- V0.249 promoted expansion family: `chat_quality_intent_grounding_boundary_adversarial`.
- V0.249 core eval: 2210/2210 passed.
- V0.249 candidate taxonomy: rows=5886, ledger_events=18062, invariants passed.
- V0.249 deterministic regression: passed=True.

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
- `project_status_out/psm_v0.249_project_status.json` is the machine status.
- Historical generated evidence remains local and is excluded from Git.
