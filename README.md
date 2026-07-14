# Property-State Model (PSM) / 物性AI

PSM is an experimental state-first AI control layer. It routes a request through explicit state, risk, evidence, audit, and release boundaries before a language-model answer can be treated as a candidate output.

物性AI的核心不是“更会接话”，而是先接状态：先识别对象、风险、证据、未知项和外部裁判，再生成自然语言。

## Current scope

- Deterministic state pipeline: `Q -> Omega -> phi -> Delta sigma -> Pi -> eta -> B_sigma -> Sigma+`.
- Candidate generation adapters, lexical auditing, deterministic gating, failure ledger, and regression artifacts.
- Local chat alpha backed by Ollama.
- Current public baseline: `PSM V0.250` (deterministic formal source: `PSM V0.249`).

This repository is an experimental research and engineering system. It is not a medical, legal, investment, production-release, or external-user authorization system. Passing synthetic regressions does not prove open-domain generalization.

## Quick start

Requirements: Python 3.11+ and, for generated chat answers, a local Ollama server with `gemma3:4b` or another configured model.

```bash
make check
make serve
```

Open `http://127.0.0.1:8765/`.

The deterministic pipeline itself uses only the Python standard library. Ollama is optional; the chat app falls back to a deterministic bounded response when the model is unavailable.

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

## Project truth and roadmap

- Human recovery point: [`outputs/psm_v0/CURRENT_STATUS.md`](outputs/psm_v0/CURRENT_STATUS.md)
- Architecture: [`outputs/psm_v0/PSM_V0_Blueprint.md`](outputs/psm_v0/PSM_V0_Blueprint.md)
- Current execution roadmap: [`outputs/psm_v0/roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`](outputs/psm_v0/roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md)

## Open-source boundary

The public repository includes code, public cases, schemas, and current architecture/roadmap documents. It excludes unpublished source manuscripts, extracted manuscript text, private local paths, model outputs, historical evidence stores, and local secrets.

Licensed under Apache-2.0. See [`LICENSE`](LICENSE).
