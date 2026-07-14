# PSM V0.250 Core Workspace

The current project status is `psm_v0.250`. The deterministic core source is `psm_v0.249` with 2210 formal cases. Targeted optional evidence `psm_v0.250_ollama_v249` covers 18 cases; ordinary output remained unsafe/risky on 6 rows while raw/gated PSM unsafe/risky stayed 0/0. Ordinary output and raw PSM output remain non-release candidates; controller-gated evidence is auxiliary only.

## Latest Result

- V0.250 local-model bakeoff selected `gemma3:4b` at mean score 0.9500 versus `deepseek-r1:8B` at 0.2850.
- The selected 180-token configuration produced 10/10 visible answers with no reasoning leaks; median latency was 5700 ms, so the 5000 ms target remains open.
- Chat generation now uses a provider abstraction and a structured answer/evidence/uncertainty/judge contract with deterministic fallback.
- V0.250 optional evidence source: `psm_v0.250_ollama_v249`.
- V0.250 targeted optional cases: 18; ordinary unsafe/risky=6; raw/gated PSM unsafe/risky=0/0.
- V0.250 release decision: `publish_psm_gated_optional_external_evidence_only`.
- V0.250 deterministic regression: passed=True.
- V0.251 engineering checkpoint: 80 authored questions, isolated judge-only labels, and two-phase NoTargetRead evaluation are implemented.
- V0.251 is not promoted: three frozen blind waves failed; the latest reached correctness=0.8583 and critical false negatives=0, but usefulness=0.4500 and safety=0.9000 missed the gate.
- Further promotion now requires an independent human or externally authorized model judge; same-developer blind-set cycling is stopped.

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
- Current promoted version remains V0.250 while the V0.251 independent-judge blocker is open.
- Rule replacement remains disabled.

## Recovery

- `CURRENT_STATUS.md` is the current human recovery point.
- `project_status_out/psm_v0.250_project_status.json` is the machine status.
- Historical generated evidence remains local and is excluded from Git.
