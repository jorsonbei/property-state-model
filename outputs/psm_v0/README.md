# PSM V0.258 Core Workspace

The current project status is `psm_v0.258`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records; V0.258 adds a source-isolated calibrated shadow state encoder and fail-closed abstention without replacing the deterministic controller.

## Latest Result

- Frozen Wave G independent semantic gate remains passed 20/20.
- V0.257 base model and training dataset are frozen by SHA-256; calibration does not change base weights.
- V0.258 uses 14 calibration, 14 evaluation, and 7 unresolved synthetic non-private records with zero cross-purpose source or duplicate overlap.
- Evaluation coverage is 0.959184, minimum selective accuracy is 0.928571, accepted critical false negatives are 0, and 4 low-confidence targets abstain.
- All 7 unresolved targets fail closed through the consensus contract; model-only disagreement detection remains an explicit 0/7 residual risk.
- Next stage: V0.259 Sigma+ traceable delivery.

## Run

From the repository root:

```bash
make check
make serve
```

## Boundaries

- Stable internal local single-user chat only.
- Ordinary and raw PSM outputs are not release candidates.
- External user trial remains closed.
- Rule replacement remains disabled.

## Recovery

- `CURRENT_STATUS.md` is the current human recovery point.
- `project_status_out/psm_v0.258_project_status.json` is the machine status.
- Historical generated evidence remains local and is excluded from Git.
