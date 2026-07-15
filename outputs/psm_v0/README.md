# PSM V0.261 Core Workspace

The current project status is `psm_v0.261`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records; V0.261 completes the authorized synthetic external contract-review loop while keeping every external-user, professional, training, rule-replacement, and release authority closed.

## Latest Result

- Frozen Wave G independent semantic gate remains passed 20/20.
- V0.260 `internal_trial_ready` remains limited to local single-user internal use.
- Formal core, independent blind, and internal Alpha evidence remain 2228/2228, 20/20, and 13/13.
- Critical fact hallucinations and critical safety false negatives are both 0.
- Seventeen residual risks remain visible; 12 are open/not-built and acceptable only inside the frozen internal boundary.
- The initial OpenAI contract review failed on five structural checks; the failure is retained.
- The closed-world V2 repair passes ten local mutation checks, including nested leaf-type and extra-target rejection, with zero candidate leakage or protected backflow.
- The final `gpt-5.4` external rejudge passes 5/5 questions with zero failed checks, critical findings, or repairs.
- Next stage: blocked V0.262 external-user scope, privacy/data, deployment, consent, retention, and budget decisions.

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
