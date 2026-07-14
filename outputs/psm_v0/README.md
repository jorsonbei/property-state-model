# PSM V0.260 Core Workspace

The current project status is `psm_v0.260`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records; V0.260 completes the local single-user internal-readiness review while keeping every external, professional, shadow-control, and rule-replacement authority closed.

## Latest Result

- Frozen Wave G independent semantic gate remains passed 20/20.
- V0.260 issues `internal_trial_ready` only for local single-user internal use.
- Formal core, independent blind, and internal Alpha evidence remain 2228/2228, 20/20, and 13/13.
- Critical fact hallucinations and critical safety false negatives are both 0.
- Seventeen residual risks remain visible; 12 are open/not-built and acceptable only inside the frozen internal boundary.
- The authorized synthetic external contract review remains unsubmitted without an API credential.
- Next stage: blocked V0.261 external-validation scope, privacy/data, deployment, budget, and credential decisions.

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
- `project_status_out/psm_v0.260_project_status.json` is the machine status.
- Historical generated evidence remains local and is excluded from Git.
