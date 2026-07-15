# PSM V0.262 Core Workspace

The current project status is `psm_v0.262`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records; V0.262 freezes and independently reviews the conservative invite-only trial protocol while keeping the real trial, public service, professional, training, rule-replacement, and release authorities closed.

## Latest Result

- Frozen Wave G independent semantic gate remains passed 20/20.
- V0.260 `internal_trial_ready` remains limited to local single-user internal use.
- Formal core, independent blind, and internal Alpha evidence remain 2228/2228, 20/20, and 13/13.
- Critical fact hallucinations and critical safety false negatives are both 0.
- The approved protocol permits only 3-5 invited adults under operator supervision, with operator adulthood verification and one-to-one secret-HMAC pseudonym binding.
- The local protocol gate passes 20/20 checks and rejects 8/8 sensitive or prohibited synthetic attacks.
- Raw participant prompts are retained for zero days and never sent to external APIs; content-free HMAC/operational metadata expires after seven days.
- The API reservation gate has a USD 20 calendar-month cap; only USD 4 has been reserved for two synthetic protocol reviews.
- The initial `gpt-5.4` protocol review failed two enrollment/notice controls and is retained. The repaired protocol passes the final 7/7 review with no remaining findings.
- Next stage: blocked V0.263 enrollment of 3-5 real invited adults. No trial session is active.

## Run

From the repository root:

```bash
make check
make serve
```

## Boundaries

- Stable internal local chat and an inactive invite-only trial protocol.
- Ordinary and raw PSM outputs are not release candidates.
- No participant is enrolled; external trial and public service remain closed.
- No sensitive or professional-decision data may enter the trial.
- Rule replacement remains disabled.

## Recovery

- `CURRENT_STATUS.md` is the current human recovery point.
- `project_status_out/psm_v0.262_project_status.json` is the machine status.
- `runtime/v0_262_external_trial_protocol_checkpoint.json` is the promotion and V0.263 blocker checkpoint.
- Historical generated evidence remains local and is excluded from Git.
