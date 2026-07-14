# Property-State Model (PSM) / 物性AI

PSM is an experimental state-first AI control layer. It routes a request through explicit state, risk, evidence, audit, and release boundaries before a language-model answer can be treated as a candidate output.

物性AI的核心不是“更会接话”，而是先接状态：先识别对象、风险、证据、未知项和外部裁判，再生成自然语言。

## Current scope

- Deterministic state pipeline: `Q -> Omega -> phi -> Delta sigma -> Pi -> eta -> B_sigma -> Sigma+`.
- Candidate generation adapters, lexical auditing, deterministic gating, failure ledger, and regression artifacts.
- Local chat alpha backed by Ollama.
- Current public baseline: `PSM V0.253` (formal 2228-record core evidence source: `PSM V0.251`).
- V0.251's fresh externally authored Wave G passed 20/20 under an independent external semantic judge; usefulness, safety, correctness, relevance, boundary quality, and hallucination control were each 1.0000 on that frozen synthetic blind wave.
- V0.252 adds a stable internal chat-product gate with cancel, timeout, retry, recovery, progressive display, hidden debug evidence, and desktop/mobile/real-backend browser regression.
- V0.253 replaces passive Omega route labels with four executable local/read-only evidence adapters and a fail-closed provenance/failure-ledger contract.

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
```

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

Open `http://127.0.0.1:8766/`. The container connects to host Ollama through `host.docker.internal`.

## Repository map

```text
outputs/psm_v0/psm_v0/             core state/audit/gate package
outputs/psm_v0/product_alpha_app/  local chat application
outputs/psm_v0/cases/              promoted deterministic cases
outputs/psm_v0/case_packs/         staged adversarial case packs
outputs/psm_v0/work/               version advancement tooling
outputs/psm_v0/runtime/            sanitized container/runtime snapshot
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
- Current execution roadmap: [`outputs/psm_v0/roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`](outputs/psm_v0/roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md)

## Open-source boundary

The public repository includes code, public cases, schemas, and current architecture/roadmap documents. It excludes unpublished source manuscripts, extracted manuscript text, private local paths, model outputs, historical evidence stores, and local secrets.

Licensed under Apache-2.0. See [`LICENSE`](LICENSE).
