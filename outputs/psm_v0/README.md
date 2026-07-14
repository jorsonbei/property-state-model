# PSM V0.259 Core Workspace

The current project status is `psm_v0.259`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records; V0.259 adds traceable Sigma+ candidate delivery while keeping the calibrated shadow encoder observation-only and deterministic control authoritative.

## Latest Result

- Frozen Wave G independent semantic gate remains passed 20/20.
- V0.259 separates the natural user answer from developer-only state, provenance, tool, failure, judge, statement, and calibrated-shadow evidence.
- Frozen evaluation passes 15/15 cases and audits 22 strong claims with 1.0 minimum provenance-or-downgrade coverage.
- Six cases exercise provenance, two failure events and 25 unresolved judges are retained, and 19 shadow targets fall back to deterministic rules.
- Ordinary debug leakage, candidate-controlled output, and external release authority are all 0.
- Next stage: V0.260 internal trial readiness review.

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
- `project_status_out/psm_v0.259_project_status.json` is the machine status.
- Historical generated evidence remains local and is excluded from Git.
