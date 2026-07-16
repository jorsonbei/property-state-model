# Property-State Model (PSM) / 物性AI

PSM is an experimental state-first AI control layer. It routes a request through explicit state, risk, evidence, audit, and release boundaries before a language-model answer can be treated as a candidate output.

物性AI的核心不是“更会接话”，而是先接状态：先识别对象、风险、证据、未知项和外部裁判，再生成自然语言。

## Current scope

- Deterministic state pipeline: `Q -> Omega -> phi -> Delta sigma -> Pi -> eta -> B_sigma -> Sigma+`.
- Candidate generation adapters, lexical auditing, deterministic gating, failure ledger, and regression artifacts.
- Local chat alpha backed by Ollama.
- Current public baseline: `PSM V0.293` (formal 2228-record core evidence source: `PSM V0.251`).
- V0.251's fresh externally authored Wave G passed 20/20 under an independent external semantic judge; usefulness, safety, correctness, relevance, boundary quality, and hallucination control were each 1.0000 on that frozen synthetic blind wave.
- V0.252 adds a stable internal chat-product gate with cancel, timeout, retry, recovery, progressive display, hidden debug evidence, and desktop/mobile/real-backend browser regression.
- V0.253 replaces passive Omega route labels with four executable local/read-only evidence adapters and a fail-closed provenance/failure-ledger contract.
- V0.254 builds a task-level Pi graph from messages and route evidence, exposes explainable graph deltas, and quarantines failure-learning candidates from blind or training backflow.
- V0.255 passes the internal chat Alpha gate across the independent blind wave, 13 current structured scenarios, real browser/Docker evidence, and zero critical fact-hallucination or safety-false-negative thresholds.
- V0.256 freezes source-isolated Q/Omega/phi/Delta sigma/Pi/eta/B_sigma annotation targets, preserves unresolved votes, audits family/source/time and duplicate contamination, and exports training-only rows under a shadow-only boundary.
- V0.257 trains the first seven-head probabilistic shadow state encoder on 14 source-isolated training rows and evaluates it on separate 14-row validation and test families; the candidate reaches 0.928571/1.0 exact match with zero critical false negatives, while deterministic rules remain the controller.
- V0.258 freezes the V0.257 model and data by SHA-256, calibrates all seven heads on an isolated 14-row family, evaluates 14 new rows plus 7 unresolved targets, and adds fail-closed abstention without changing base weights or granting release authority.
- V0.259 adds a Sigma+ delivery contract that keeps natural answers separate from developer traces, requires provenance or explicit downgrades for strong claims, and retains calibrated shadow observations without granting them output authority.
- V0.260 completes a frozen internal-readiness review: 2228/2228 formal cases, 20/20 independent blind rows, 13/13 internal Alpha scenarios, zero critical fact hallucinations or safety false negatives, and an `internal_trial_ready` decision limited to local single-user use.
- V0.261 retains an initial failed OpenAI contract review, repairs the annotation boundary as a closed-world V2 schema, passes ten local mutation checks including nested leaf-type and extra-target rejection with zero candidate leakage or protected backflow, and then passes a five-question `gpt-5.4` external rejudge with no remaining findings. External users and release authority remain closed.
- V0.262 freezes the approved conservative invite-only trial protocol for 3-5 operator-supervised adults, rejects sensitive and professional-decision prompts, retains no raw participant chat, keeps content out of external APIs, deletes content-free metadata after seven days, and enforces a USD 20 monthly API reservation cap. The initial independent protocol review failed on two enrollment/notice controls; after repair, the final seven-question `gpt-5.4` review passes with no remaining findings.
- V0.263 records three complete operator-attested enrollment sequences, three passing private access checks, and the first content-free supervised low-risk session evidence. Desktop/mobile and Docker boundaries pass; invitation values remain outside Git and Docker. This activates only the local supervised invite-only trial, not a public service or privacy-compliance claim.
- V0.264 completes and promotes the bounded three-person pilot: P01-P03 each reached 3/3 credited low-risk turns, with 20 content-free allowed events, zero raw prompt/answer retention, and zero participant-content external API calls.
- V0.265 replaces the cancelled human-rating gate with 30 frozen synthetic quality cases, including 12 simulated user roles. All 30 cases and all 12 role-proxy rubrics pass, with zero critical factual hallucinations and zero critical safety false negatives. The evidence is synthetic and does not claim real-user satisfaction or human validation.
- V0.266 freezes 15 adversarial metamorphic pairs and 30 variants across paraphrase, role history, negation, event time, and release boundaries. Eight initial failing pairs are retained before repair; the final suite passes 15/15 and 30/30 with zero critical factual hallucinations, safety false negatives, or evaluation backflow.
- V0.267 sends a sanitized, source-isolated synthetic package to `gpt-5.4`. Three failed external attempts are retained, the resulting translation/rewrite findings are repaired locally, and the final independent review passes all 15/15 pairs with no critical findings.
- V0.268 measures whether normal chat actually completes translation, rewriting, extraction, comparison, summarization, planning, and explanation tasks. Five initial failures and three transparent contract errata are retained; the final frozen suite passes 21/21 with no provider-failure substitute or task-restatement substitute.
- V0.269 repeats seven representative tasks three times and passes 21/21 semantic invariants with zero provider or deterministic drift; local p50/p95 are 23 ms/16.771 s, and real cancel, timeout, retry, empty-response, offline-provider, browser, and Docker recovery gates pass.
- V0.270 passes 12/12 frozen multi-turn cases after retaining five initial failures. It preserves assistant references, explicit topic switches, user corrections, literal exclusions, three-step formatting, and translation-only constraints without assistant-history contamination.
- V0.271 retains its first `gpt-5.4` failure on M07/M08, repairs both over-answers locally, and then passes a separately authorized 12/12 independent rejudge with zero failed items or critical findings. The one post-write runner reporting failure is retained and did not trigger an API retry. The evidence is synthetic and grants no external release authority.
- V0.274 retains a 0/10 first open-context run, adds a user-authoritative state capsule and broader correction, unresolved-work, constraint-inheritance, and topic-switch handling, then passes 10/10 with zero stale-state violations. Desktop/mobile and host/Docker boundaries pass; V0.273 also independently passed 10/10 with one authorized external call.
- V0.275 retains two independent failed reviews, repairs O01/O02/O09/O10 locally, and then passes a third 10/10 `gpt-5.4` review with zero critical findings. Synthetic external judging is now governed by a cumulative 1,000,000-token user authorization.
- V0.276-V0.279 extend durable state recovery from 43 to 119 messages. The V0.276 baseline failed 10/10; final local gates pass 10/10, and two source-isolated external reviews pass 10/10. The 81/119-message stress P95 is 30 ms.
- V0.280 adds rolling state handoff after the original fact exits the 120-message product window. The retained truncation baseline failed 4/4; final local and host/Docker gates pass 4/4 while keeping at most 20 user statements in ephemeral memory for 30 minutes, with no user-statement disk persistence.
- V0.281 passes 11 session isolation, expiry, replay, and capacity checks plus a 4/4 independent external semantic review. V0.282 passes a real Playwright desktop/mobile lifecycle regression: the cross-window answer is visible, reset/reload rotate sessions, layout overflow is zero, and browser console errors are zero.
- V0.283 makes active, reset, reload, expired, and restarted continuity states user-visible without persisting raw chat. The retained baseline is 0/5; final host, Docker, desktop, and mobile recovery gates pass 5/5 with zero archived-fact fabrication.
- V0.284 independently reviews the five lifecycle answers with `gpt-5.4` and passes 5/5. V0.285 closes same-session memory resurrection after reset/reload/stale-instance replay, passes 8/8, isolates 32 concurrent sessions, and keeps 128 one-hour hash-only expiry tombstones.
- V0.286 expands prior-reference detection beyond fixed phrases. The retained baseline is 4/16; final detection is 16/16 with 48 memory-loss answer checks and zero archived-fact fabrication.
- V0.287 independently reviews all 12 natural-reference cases and four explicit-new-task controls with `gpt-5.4`; all 16 pass. Cumulative synthetic OpenAI judge usage is 157,268 / 1,000,000 authorized tokens.
- V0.288 passes the same 16 cases on both host and Docker, including server-owned expiry eviction, with zero synthetic sentinel writes to disk. V0.289 passes real Chromium desktop/mobile recovery and new-task interaction with zero overflow or console errors.
- V0.290 measures host and Docker latency. Deterministic recovery/identity P95 stays below 38 ms; six normal local-model generations all succeed with zero fallback, with observed P50/P95 around 13.4-16.4 / 16.7 seconds.
- V0.291 validates staged progress, cancel, prompt preservation, retry, and single-turn integrity in a real browser. Observed client cancellation is 37 ms; this does not claim server-side inference cancellation or network token streaming.
- V0.292 adds bounded in-memory request cancellation and closes the server-owned Ollama connection without displaying partial model chunks. Host/Docker cancel 6/6 active requests, with observed maximum worker-stop latency of 38.49/276.25 ms; desktop/mobile browser and 249-test regressions pass. Direct model-kernel/GPU stop instrumentation and network token streaming remain unclaimed.
- V0.293 caps active chat admission at four with no hidden queue. Four host/Docker waves cancel 16/16 active requests, reject every fifth request with structured 503, reject duplicate IDs with 409, preserve active work, and recover capacity. Browser backpressure recovery and 252/252 regression pass; unexpected console errors and raw-text disk writes are zero.

This repository is an experimental research and engineering system. It is not a medical, legal, investment, production-release, or external-user authorization system. Passing synthetic regressions does not prove open-domain generalization.

## Quick start

Requirements: Python 3.11+ and, for generated chat answers, a local Ollama server with `qwen3.5:9b` or another configured model.

```bash
make check
make serve
```

Open `http://127.0.0.1:8765/`.

The deterministic pipeline itself uses only the Python standard library. Ollama is optional; the chat app falls back to a deterministic bounded response when the model is unavailable.

Install and run the browser regression harness:

```bash
make browser-install
make browser-regression
PSM_BASE_URL=http://127.0.0.1:8765 make browser-regression-real
make route-v253-eval
make route-v253-docker
make state-v254-eval
make state-v254-docker
make alpha-v255-eval
make alpha-v255-docker
make annotation-v256-eval
make annotation-v256-docker
make encoder-v257-eval
make encoder-v257-docker
make calibrate-v258-eval
make calibrate-v258-docker
make sigma-v259-eval
make sigma-v259-docker
make readiness-v260-review
make readiness-v260-docker
make repair-v261-eval
make judge-v261-openai
make external-v261-docker
make protocol-v262-eval
make judge-v262-openai
make promote-v262
make external-v262-docker
make prepare-v263
make browser-regression-v263-enrollment
make enrollment-v263-docker
make pilot-v264-eval
make pilot-v264-docker
make quality-v265-eval
make browser-regression-v265-quality
make quality-v265-docker
make promote-v265
make adversarial-v266-eval
make browser-regression-v266-adversarial
make adversarial-v266-docker
make promote-v266
make prepare-v267
make judge-v267-openai
make repair-v267-external
make browser-regression-v267-external
make external-v267-docker
make promote-v267
make task-v268-eval
make browser-regression-v268-task
make task-v268-docker
make promote-v268
make stability-v269-eval
make browser-regression-v269-stability
make stability-v269-docker
make promote-v269
make multiturn-v270-eval
make browser-regression-v270-multiturn
make multiturn-v270-docker
make promote-v270
make prepare-v271
make judge-v271-openai
make repair-v271-local
make authorize-v271-rejudge
make rejudge-v271-openai
make finalize-v271
make promote-v271
make long-context-v272-eval
make browser-regression-v272-long-context
make long-context-v272-docker
make promote-v272
make prepare-v273
make build-v276
make long-horizon-v276-eval
make prepare-v277
make judge-v277-openai
make build-v278
make stress-v278-eval
make prepare-v279
make judge-v279-openai
make build-v280
make rolling-v280-eval
make isolation-v281-eval
make prepare-v281
make judge-v281-openai
make browser-v282-rolling
make build-v283
make recovery-v283-eval
make runtime-v283-restart
make browser-v283-recovery
make prepare-v284
make judge-v284-openai
make build-v285
make integrity-v285-eval
make integrity-v285-runtime
make build-v286
make recovery-v286-eval
make prepare-v287
make judge-v287-openai
make runtime-v288-parity
make browser-v289-recovery
make build-v290
make latency-v290-eval
make browser-v291-cancel
make server-cancel-v292-eval
make browser-v292-cancel
make concurrency-v293-eval
make browser-v293-backpressure
```

The historical local operator page is `http://127.0.0.1:8765/trial-enrollment`. It displays the completed V0.264 supervised-pilot record. V0.274 collects no participant ratings and requires no human actions.

Generate a read-only inventory of the local evidence store without moving or deleting artifacts:

```bash
make inventory
```

## Docker

Docker is optional and keeps the public runtime isolated from the multi-gigabyte local evidence store. Docker Desktop must be running, and Ollama remains on the host:

```bash
make sync-runtime
docker compose up --build
```

Open `http://127.0.0.1:8766/`. Docker publishes only on the local loopback interface, and the container connects to host Ollama through `host.docker.internal`. The Docker runtime excludes V0.263 private invitations and contains no human-feedback module, state, UI, or endpoint.

## Repository map

```text
outputs/psm_v0/psm_v0/             core state/audit/gate package
outputs/psm_v0/product_alpha_app/  local chat application
outputs/psm_v0/cases/              promoted deterministic cases
outputs/psm_v0/case_packs/         staged adversarial case packs
outputs/psm_v0/work/               version advancement tooling
outputs/psm_v0/runtime/            sanitized container/runtime snapshot
outputs/psm_v0/private_runtime/    ignored owner-only historical enrollment state
scripts/                            project verification and snapshot tools
tests/                              public contract tests
```

Large generated evidence directories and private manuscript extraction materials are intentionally excluded from Git and Docker build contexts.

Recompute the checked-in V0.251 external semantic judgment:

```bash
make judge-v251-external
```

## Project truth and roadmap

- Human recovery point: [`outputs/psm_v0/CURRENT_STATUS.md`](outputs/psm_v0/CURRENT_STATUS.md)
- Architecture: [`outputs/psm_v0/PSM_V0_Blueprint.md`](outputs/psm_v0/PSM_V0_Blueprint.md)
- Current execution checkpoint: [`outputs/psm_v0/runtime/v0_291_cancel_retry_checkpoint.json`](outputs/psm_v0/runtime/v0_291_cancel_retry_checkpoint.json)

## Open-source boundary

The public repository includes code, public cases, schemas, and current architecture/roadmap documents. It excludes unpublished source manuscripts, extracted manuscript text, private local paths, model outputs, historical evidence stores, and local secrets.

Licensed under Apache-2.0. See [`LICENSE`](LICENSE).
