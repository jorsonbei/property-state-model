# PSM Invite-Only Trial Roadmap V0.262 to V0.263

## Completed V0.262

1. Freeze the approved conservative protocol for 3-5 invited adults under operator supervision.
2. Require pre-vetted adulthood, operator verification, and one-to-one secret-HMAC invitee/pseudonym binding.
3. Enforce notice display, acknowledgment, explicit consent, and session enablement in that order.
4. Reject direct identifiers, secrets, minors, private documents, and medical, legal, or trading decision requests.
5. Retain raw participant prompts for zero days and prohibit participant content from every external API call.
6. Retain only content-free HMAC and operational metadata, with seven-day expiry and withdrawal deletion.
7. Reserve external API cost before each call under a USD 20 calendar-month cap.
8. Pass 20/20 local checks and reject 8/8 synthetic attack prompts.
9. Retain the initial two-check external review failure, repair both controls, and pass the final 7/7 independent review with no remaining findings.
10. Keep the trial, public service, professional authority, trial-data training, rule replacement, and release authority inactive.

## Completed V0.263 Engineering Preparation

1. Freeze the user's choice of exactly three participants without inferring presence, adulthood, or consent.
2. Generate three unique local invitations for P01-P03 in owner-only storage backed by a Keychain binding secret.
3. Implement the strict five-step enrollment state machine and require all three receipts before the first message.
4. Add a local operator page with masked invitation codes and no direct-identity input fields.
5. Stop all sessions without automatic resume when sensitive or unknown data is detected; delete a withdrawing participant's operational audit events.
6. Pass desktop and mobile browser regression with no human action executed and all human counts at zero.
7. Prove that private invitation material is absent from Git-tracked files and the Docker image; the container cannot access enrollment cards or trial chat.

## V0.263 Human Enrollment Gate

V0.263 now requires the three selected real people and cannot be completed from code alone. All three invited adults must attend a supervised local trial session with the operator physically present.

Do not submit participant names, contact details, identity documents, or other direct identifiers in Codex, GitHub, issue trackers, or project files. The operator verifies adulthood outside the system. The software then creates a local pseudonymous invitation and secret-HMAC binding without storing direct identity.

For each participant, the required order is:

1. Confirm the person belongs to the pre-vetted adult invite list.
2. Complete operator adulthood verification and local pseudonymous binding.
3. Display the frozen V0.262 notice.
4. Record notice acknowledgment.
5. Record explicit consent.
6. Enable the supervised session only after every prior gate passes.

The first real participant prompt is prohibited until all three enrollment receipts pass the gate. Any privacy, security, sensitive-data, budget, deletion, supervision, or consent failure stops the trial without automatic resume.

Current counts: invited 3; adult verified 0; notice acknowledged 0; explicitly consented 0; session enabled 0. Operator URL: `http://127.0.0.1:8765/trial-enrollment`.

## Still Closed

- Public signup or internet exposure.
- Unsupervised or remote access.
- Sensitive, private, medical, legal, or trading-decision data.
- Privacy-compliance, production-readiness, or professional-authority claims.
- Training or tuning on trial data.
- Rule replacement or external release authority.
