# PSM V0.247 Core Workspace

This directory contains the Property-State Model core, public deterministic cases, local chat alpha, and version-advancement tools. Generated evidence is kept locally but excluded from Git.

## Current result

- Formal core: 2192 cases.
- Candidate gate: 1939 cases.
- Gated unsafe/risky: 0.
- Regression: passed.
- Internal local demo: open.
- External user trial: closed.

## Run

From the repository root:

```bash
make check
make serve
```

## Structure

- `psm_v0/`: state extraction, routing, audit, gating, datasets, and reports.
- `product_alpha_app/`: local chat server and static UI.
- `cases/`: promoted deterministic cases.
- `case_packs/`: staged adversarial packs.
- `work/`: controlled version advancement.
- `runtime/`: sanitized runtime snapshot used by Docker.
- `*_out/`: generated local evidence, not committed.

## Recovery

- Current human status: `CURRENT_STATUS.md`.
- Machine status: `project_status_out/psm_v0.247_project_status.json`.
- Current roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

The historical append-only status was archived locally under `status_history/`. New versions write one concise current status plus one version-specific history snapshot.
