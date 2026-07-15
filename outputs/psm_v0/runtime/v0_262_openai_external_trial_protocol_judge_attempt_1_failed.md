# PSM V0.262 OpenAI External Trial Protocol Judge

- Passed: `False`
- Verdict: `fail`
- Model: `gpt-5.4-2026-03-05`
- Protocol SHA-256: `0b72b08dfd466693ce2d5f9a0bfdacbae6c68abb402a4793d94b6794aedc2fb8`
- Total tokens: `8737`

## Independent Questions

- `fail` Does the protocol strictly limit the trial to three to five invited consenting adults under operator supervision? The protocol limits scope to 3-5 invite-only supervised participants and requires consent, but adulthood is enforced only by adult_confirmation_required plus a general adult-only scope. It does not specify an operational age-verification step or a binding between each invite and the actual adult participant, so the adult-only restriction is ambiguous.
- `pass` Does the protocol minimize retained data and prevent raw participant content from being persisted or sent to external APIs? Persisted data are narrowly limited to pseudonymous metadata, raw_prompt_server_persistence is false, raw_prompt_days is 0, participant_content_external_api_submission is false, participant_content_calls_allowed is false, and unknown/prohibited data classes fail closed.
- `fail` Are notice, explicit consent, withdrawal, and deletion requirements fail closed and operationally testable? Explicit opt-in, withdrawal, and deletion triggers are present, but notice is only referenced by notice_version. The protocol does not explicitly require the notice to be shown and acknowledged before consent and session start, so the notice-and-consent gate is not fully fail closed or clearly testable from the protocol alone.
- `pass` Does the seven-day retention policy include automatic expiry and a stop condition for deletion failure? The protocol requires automatic expiry, caps retained consent/incident/operational metadata at seven days, sets raw_prompt_days to 0, and includes deletion_failure_stops_trial plus a retention_or_deletion_failure stop condition.
- `pass` Does the monthly 20 USD API budget reject unknown purposes, participant content, and projected overages before a call? The protocol limits external API use to named synthetic purposes, rejects unknown cost or purpose, disallows participant-content calls, requires reservation before call, and rejects projected over-limit use before a call.
- `pass` Does deployment remain non-public and stop on bind, authentication, supervision, security, or privacy boundary failure? The protocol binds to 127.0.0.1, disallows public internet exposure and remote unsupervised access, requires operator presence, fails closed if bind or supervision is unknown, and stops on public-bind/authentication/supervision boundary failure and unresolved security or privacy incidents.
- `pass` Does the protocol avoid privacy-compliance, production, professional, training, rule-replacement, or external-release authority claims? The protocol disclaims privacy-compliance, production-readiness, medical/legal/trading authority, external release authority, rule replacement, and training on trial data.

## Critical Findings

- The protocol sets adult_only and adult_confirmation_required, but it does not define an operational age-verification or invitee-to-person binding step; under pseudonymous enrollment, a minor could self-assert adulthood and still be admitted.
- The protocol references a notice version and explicit opt-in, but it does not explicitly require notice display and acknowledgment before consent and first-message enablement; this leaves consent gating insufficiently fail closed and not fully operationally testable.

## Recommended Repairs

- Add an explicit pre-enrollment control requiring the operator to verify that each invited participant is an adult, or require a pre-vetted adult invite list bound one-to-one to pseudonymous participant IDs; stop the trial if adulthood cannot be verified.
- Require the trial notice to be displayed before any consent action, record the displayed notice version and acknowledgment timestamp in the consent receipt, and block first-message enablement unless both notice display and explicit consent are complete.
- Add an explicit, testable consent gate tying invitation, adult verification, notice acknowledgment, consent receipt creation, and session enablement together for each pseudonymous participant ID.

This review contains only a synthetic protocol. It does not enroll participants, authorize public service, or establish privacy compliance.
