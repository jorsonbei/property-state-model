# Property-State Model (PSM) / 物性AI

PSM is an experimental state-first AI control layer. It routes a request through explicit state, risk, evidence, audit, and release boundaries before a language-model answer can be treated as a candidate output.

物性AI的核心不是“更会接话”，而是先接状态：先识别对象、风险、证据、未知项和外部裁判，再生成自然语言。

## Current scope

- Deterministic state pipeline: `Q -> Omega -> phi -> Delta sigma -> Pi -> eta -> B_sigma -> Sigma+`.
- Candidate generation adapters, lexical auditing, deterministic gating, failure ledger, and regression artifacts.
- Local chat alpha backed by Ollama.
- Current public baseline: `PSM V0.263` (formal 2228-record core evidence source: `PSM V0.251`).
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
- V0.264 is staged as a bounded three-person pilot. Each pseudonymous participant must complete at least three low-risk general turns; current progress is available on the local operator page without storing raw prompts or answers.

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
```

The V0.264 local operator page is `http://127.0.0.1:8765/trial-enrollment`. It shows each pseudonymous participant's `x/3` low-risk turn progress. It is only for use while the invited adult and operator are physically present. Do not enter or store names, contact details, identity documents, secrets, or medical, legal, and trading-decision data.

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

Open `http://127.0.0.1:8766/`. Docker publishes only on the local loopback interface, and the container connects to host Ollama through `host.docker.internal`. The Docker runtime intentionally excludes V0.263 private invitations and cannot perform participant enrollment.

## Repository map

```text
outputs/psm_v0/psm_v0/             core state/audit/gate package
outputs/psm_v0/product_alpha_app/  local chat application
outputs/psm_v0/cases/              promoted deterministic cases
outputs/psm_v0/case_packs/         staged adversarial case packs
outputs/psm_v0/work/               version advancement tooling
outputs/psm_v0/runtime/            sanitized container/runtime snapshot
outputs/psm_v0/private_runtime/    ignored owner-only V0.263 enrollment state
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
- Current execution roadmap: [`outputs/psm_v0/roadmap_out/PSM_Supervised_Pilot_Roadmap_V0.263_to_V0.264.md`](outputs/psm_v0/roadmap_out/PSM_Supervised_Pilot_Roadmap_V0.263_to_V0.264.md)

## Open-source boundary

The public repository includes code, public cases, schemas, and current architecture/roadmap documents. It excludes unpublished source manuscripts, extracted manuscript text, private local paths, model outputs, historical evidence stores, and local secrets.

Licensed under Apache-2.0. See [`LICENSE`](LICENSE).
