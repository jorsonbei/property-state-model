# PSM V0.248 Core Workspace

The current project status is `psm_v0.248`. The deterministic core source is `psm_v0.247` with 2192 formal cases. Targeted optional evidence `psm_v0.248_ollama_v247` covers 18 cases; ordinary output remained unsafe/risky on 16 rows while raw/gated PSM unsafe/risky stayed 0/0. Ordinary output and raw PSM output remain non-release candidates; controller-gated evidence is auxiliary only.

## Latest Result

- V0.248 optional evidence source: `psm_v0.248_ollama_v247`.
- V0.248 targeted optional cases: 18; ordinary unsafe/risky=16; raw/gated PSM unsafe/risky=0/0.
- V0.248 release decision: `publish_psm_gated_optional_external_evidence_only`.
- V0.248 deterministic regression: passed=True.

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
- `project_status_out/psm_v0.248_project_status.json` is the machine status.
- Historical generated evidence remains local and is excluded from Git.
