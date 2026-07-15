# PSM V0.264 Core Workspace

The current promoted project status is `psm_v0.264`. The deterministic formal evidence source remains `psm_v0.251` with 2228 records. V0.264 adds the completed three-person supervised pilot; V0.265 is an unpromoted structured-feedback stage.

## Latest Result

- P01-P03 each completed at least three supervised low-risk turns, with credited coverage of 3/3 each.
- The V0.264 gate contains 20 allowed low-risk content-free events, zero rejected events, zero retained raw prompts/answers, and zero participant-content external API calls.
- V0.264 desktop/mobile browser and Docker isolation checks pass.
- V0.265 implements one-time HMAC-bound feedback for each new eligible turn using four fixed fields and no free text.
- V0.265 desktop/mobile browser and Docker isolation checks pass without writing synthetic feedback into the real participant state.
- Current V0.265 feedback progress is P01 0/3, P02 0/3, and P03 0/3; quality thresholds remain unevaluated until coverage is complete.

## Run

From the repository root:

```bash
make check
make serve
make feedback-v265-eval
make browser-regression-v265-feedback
make feedback-v265-docker
```

The operator page is `http://127.0.0.1:8765/trial-enrollment`. Each invited adult must remain physically supervised. Never enter direct identity data, contact details, secrets, private documents, medical/legal requests, or trading decisions.

## Boundaries

- The active product scope is a local invite-only supervised trial, not a public service.
- Feedback is subjective pilot evidence only. It does not authorize training, rule replacement, production use, professional action, privacy-compliance claims, or external release.
- Raw participant prompts and answers are retained for zero days and are not sent to external APIs.
- Private invitations and feedback state are owner-only, ignored by Git, and excluded from Docker.
- Withdrawal deletes that participant's content-free audit events and structured feedback.

## Recovery

- `CURRENT_STATUS.md` is the current human recovery point.
- `project_status_out/psm_v0.264_project_status.json` is the machine status.
- `runtime/v0_264_supervised_pilot_promotion_manifest.json` records the current promotion.
- `runtime/v0_265_structured_feedback_checkpoint.json` is the current human gate.
- `runtime/v0_265_structured_feedback_browser_regression/report.json` records UI evidence.
- `runtime/v0_265_structured_feedback_docker_boundary.json` records container isolation.
- `roadmap_out/PSM_Structured_Feedback_Roadmap_V0.264_to_V0.265.md` is the active roadmap.

Historical generated evidence remains local and excluded from Git where configured.
