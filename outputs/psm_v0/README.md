# PSM V0.265 Core Workspace

The current promoted project status is `psm_v0.265`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records. V0.265 adds an automated internal quality gate and simulated-persona coverage without changing the formal core.

## Latest Result

- The frozen V0.265 suite passes 30/30 cases across conversation, grounded facts, research, theory, and high-risk boundaries.
- Twelve simulated personas pass 12/12 objective proxy rubrics for helpfulness, clarity, state alignment, and safety.
- Critical factual hallucinations and critical safety false negatives are both zero.
- Desktop/mobile browser regression and Docker isolation pass; normal chat contains no rating form.
- The human-feedback endpoint, storage module, private state, and UI have been removed.
- V0.264's completed three-person supervised-pilot evidence remains unchanged as historical evidence.

## Run

From the repository root:

```bash
make check
make serve
make quality-v265-eval
make browser-regression-v265-quality
make quality-v265-docker
make promote-v265
```

The normal chat is `http://127.0.0.1:8765/`. The historical operator page at `/trial-enrollment` displays the completed V0.264 record and does not collect V0.265 feedback.

## Boundaries

- V0.265 evidence is internally authored and synthetic; persona roleplay is not real-user evidence.
- No P01-P03 impersonation, human rating, subjective satisfaction inference, or human-validation claim is allowed.
- Evaluation rows cannot become training truth or grant rule-replacement authority.
- Public service, production readiness, professional action, privacy-compliance claims, and external release authority remain closed.
- Private V0.263 invitations remain owner-only, ignored by Git, and excluded from Docker.

## Recovery

- `CURRENT_STATUS.md` is the current human recovery point.
- `project_status_out/psm_v0.265_project_status.json` is the machine status.
- `runtime/v0_265_automated_quality_promotion_manifest.json` records the current promotion.
- `runtime/v0_265_automated_quality_gate.json` and `runtime/v0_265_automated_quality_report.json` record the frozen audit.
- `runtime/v0_265_automated_quality_browser_regression/report.json` records UI evidence.
- `runtime/v0_265_automated_quality_docker_boundary.json` records container isolation.
- `roadmap_out/PSM_Automated_Quality_Roadmap_V0.265_to_V0.266.md` is the active roadmap.

Historical generated evidence remains local and excluded from Git where configured.
