# PSM Current Status

## Current Version

`PSM V0.250`

The current project status is `psm_v0.250`. The deterministic core source is `psm_v0.249` with 2210 formal cases. Targeted optional evidence `psm_v0.250_ollama_v249` covers 18 cases; ordinary output remained unsafe/risky on 6 rows while raw/gated PSM unsafe/risky stayed 0/0. Ordinary output and raw PSM output remain non-release candidates; controller-gated evidence is auxiliary only.

## Latest Completed Result

- Frozen local-model bakeoff: 10 same-question cases across `gemma3:4b` and `deepseek-r1:8B`, scored under anonymized candidate IDs.
- Selected local chat model: `gemma3:4b`, mean score=0.9500, expected/boundary coverage=0.95/0.95, visible answers=10/10, reasoning leaks=0.
- Selected runtime configuration: timeout=45 seconds, max_tokens=300, with one expanded retry when Ollama reports token-limit termination; the <5000 ms latency target remains unmet.
- `deepseek-r1:8B` is not a fallback: its original 180-token run spent all 10 rows in reasoning blocks and produced no acceptable fallback profile.
- Structured generation contract now separates answer, grounded facts, uncertainties, required judges, provider/model, latency, and fallback status.
- Deterministic core source remains `psm_v0.249` with 2210 formal cases.
- Full all-family required/fault external run: 1957 cases.
- Full run gated PSM unsafe/risky: 0.
- Full run fault injection events: 7148.
- Full run controller rescue count: 1957.
- Targeted Ollama `['v249_']` run: 18 cases.
- Targeted optional ordinary unsafe/risky: 6.
- Targeted optional raw/gated PSM unsafe/risky: 0/0.
- Targeted optional controller-changed rows: 18.
- Targeted optional controller-rescued rows: 0.
- Targeted external taxonomy: rows=87, ledger_events=156, invariants_passed=True.
- External taxonomy delta: changed_groups=79, unexpected_regression=False.
- Risk analysis: optional_rows=18, raw_psm_risky_rows=0, controller_rescued_rows=0, gated_psm_risky_rows=0.
- Optional external regression: passed=True, checks=19.
- Hardening check: passed with fresh `psm_v0.250_ollama_v249` evidence.
- Evidence trend: passed=True; latest generation is `psm_v0.250_ollama_v249`.
- Release summary: passed=True, decision=publish_psm_gated_optional_external_evidence_only.
- Project status: `project_status_out/psm_v0.250_project_status.json`.
- Regression: passed=True with `psm_v0.249` as the deterministic core source.
- At completion, the assigned next stage is `PSM_V0.251`.

## V0.251 Checkpoint

- Implemented an 80-question authored, source-family-split chat set with 40 train, 20 dev, and 20 frozen blind rows per wave.
- Generation and scoring are separate commands; generation has no judge-file parameter and records `generation_read_judge_labels=false`.
- Latest dev result: usefulness=0.9000, safety=1.0000, correctness=0.9500, relevance/actionability/boundary/multi-turn/hallucination=1.0000, critical safety false negatives=0.
- Blind A/B/C remained failed and are sealed as non-promotable internal evidence.
- Authorized cross-provider external adjudication is complete for waves C-F. Wave D: 12/20, usefulness=0.6000, correctness=0.6750, hallucination=0.7125. Wave E after generalized repair: 15/20, usefulness=0.7500, correctness=0.8375, hallucination=0.9000. Fresh wave F: 12/20, usefulness=0.6000, correctness=0.7750, hallucination=0.8125.
- External safety stayed 1.0000 with zero critical safety failures in C-F. The remaining failure is open-domain usefulness, correctness, and hallucination control rather than the safety controller.
- Verified factual kernels, deterministic local-project routing, token-limit detection, and one expanded retry are implemented with paraphrase tests. Wave F still exposed broad 4B-base limitations across unrelated domains.
- `PSM V0.251` is not promoted. The current action is to benchmark `qwen3.5:9b` locally; only a materially better fixed-benchmark result may proceed to fresh wave G.

## Next Stage

`PSM V0.251`

Protect the independent chat golden and blind-set contract: authored questions, source-based splits, non-backflow blind rows, separate usefulness and safety reporting, and domain-specific blind evidence must not become training truth, open-domain generalization, release approval, clinical validation, profitability, or theory proof.

- Blocked: false. External judge authorization and the first independent adjudication are complete.
- Requires user input: false. `qwen3.5:9b` is being downloaded and will be tested against the fixed provider-selection contract. If it improves quality, the next evidence is a fresh externally authored wave G and cross-provider judgment; waves C-F stay sealed.
- External user trial remains closed.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.250_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.
- V0.251 checkpoint: `runtime/v0_251_chat_gate_checkpoint.json`.
- Latest V0.251 external judge evidence: `runtime/v0_251_wave_f_external_semantic_judge.json`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
