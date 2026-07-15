# PSM Current Status

## Current Version

`PSM V0.262`

The current project status is `psm_v0.262`. V0.262 freezes the user-approved conservative invite-only external trial protocol while retaining `psm_v0.251` as the formal 2228-record core evidence source and preserving the V0.260 local `internal_trial_ready` boundary.

## Latest Completed Result

- Trial scope is limited to 3-5 pre-vetted invited adults under operator supervision; self-asserted adulthood is insufficient.
- Every participant requires operator adulthood verification and a one-to-one secret-HMAC binding between the vetted invitee and local pseudonym.
- The notice must be displayed and acknowledged before explicit consent; session enablement must occur last.
- Raw participant prompts have zero server retention and may never be sent to OpenAI or another external API.
- Only content-free HMAC, risk, latency, and token metadata may be retained, with automatic deletion after seven days and withdrawal deletion support.
- The API reservation gate enforces a USD 20 calendar-month cap before any call. Two synthetic protocol reviews reserved USD 4; participant-content calls remain zero.
- The local gate passes 20/20 checks and rejects 8/8 synthetic sensitive/professional/minor attack prompts.
- The first independent `gpt-5.4-2026-03-05` review returned `fail` on two adult-enrollment and notice-order controls; the failure remains retained.
- After those controls were made operational, the final independent review passes 7/7 questions with zero failed checks, critical findings, or recommended repairs.
- The user selected exactly three participants. This records only the cohort size; it does not assert presence, adulthood, notice acknowledgment, or consent.
- Three unique local pseudonymous invitations (P01-P03) now exist in owner-only storage. Invitation codes are absent from Git, public status, browser screenshots, and Docker.
- The local enrollment UI implements the strict adult verification, notice display, acknowledgment, explicit consent, and operator-supervision sequence. Desktop and mobile browser regression pass without executing any human action.
- A prohibited or unknown data disclosure now rejects the message, records only a content-free HMAC event, stops every trial session, and forbids automatic resume. Withdrawal also stops the trial and deletes that participant's operational audit events.
- Docker publishing is restricted to `127.0.0.1`; the container contains the public V0.263 checkpoint but no private enrollment state. Enrollment APIs are unavailable and trial chat remains rejected.
- No real participant is enrolled: adult verification, notice acknowledgment, consent, and session enablement are each 0/3. No external trial session is active.
- Public service, privacy-compliance claims, professional authority, trial-data training, rule replacement, and external release authority remain closed.

## Next Stage

`PSM V0.263`

Complete the first real invite-only cohort under the frozen V0.262 protocol:

- the selected cohort is fixed at three; all three invited adults and the operator must be physically present;
- do not place names, contact details, identity documents, or other direct identifiers in chat, Git, or project artifacts;
- use the already-generated P01-P03 local invitations and bind each one to a pre-vetted adult using the existing secret HMAC;
- display the frozen notice, record acknowledgment and explicit consent, then enable the session;
- keep the trial inactive unless every enrollment gate passes.

Operator URL: `http://127.0.0.1:8765/trial-enrollment`.

- Blocked: true.
- Requires user input: true.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.262_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Frozen protocol: `benchmarks/v0_262_invite_only_external_trial_protocol.json`.
- Participant notice: `V0_262_INVITE_ONLY_TRIAL_NOTICE.md`.
- Local gate: `runtime/v0_262_external_trial_protocol_gate.json`.
- Initial failed review: `runtime/v0_262_openai_external_trial_protocol_judge_attempt_1_failed.json`.
- Final passing review: `runtime/v0_262_openai_external_trial_protocol_judge.json`.
- Promotion checkpoint: `runtime/v0_262_external_trial_protocol_checkpoint.json`.
- Three-person selection contract: `benchmarks/v0_263_three_participant_enrollment_contract.json`.
- V0.263 public checkpoint: `runtime/v0_263_participant_enrollment_checkpoint.json`.
- Enrollment browser evidence: `runtime/v0_263_enrollment_browser_regression/report.json`.
- Enrollment Docker boundary: `runtime/v0_263_enrollment_docker_boundary.json`.
- Current execution roadmap: `roadmap_out/PSM_Invite_Only_Trial_Roadmap_V0.262_to_V0.263.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
