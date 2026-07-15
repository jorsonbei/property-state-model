# PSM V0.262 OpenAI External Trial Protocol Judge

- Passed: `True`
- Verdict: `pass`
- Model: `gpt-5.4-2026-03-05`
- Protocol SHA-256: `e6b0f03e2115f783c6af39d3a7dcc9441a04bc7e936cc3f28e884e6a1acfb6b7`
- Total tokens: `3981`

## Independent Questions

- `pass` Does the protocol strictly limit the trial to three to five invited consenting adults under operator supervision? Pass. The frozen protocol limits participation to a pre-vetted adult invite list with participant_minimum 3 and participant_maximum 5, requires operator presence and supervised local use, rejects unknown or unverified adulthood, and requires explicit opt-in consent before first message with session enablement blocked until prior consent steps are completed.
- `pass` Does the protocol minimize retained data and prevent raw participant content from being persisted or sent to external APIs? Pass. Persisted data is narrowly limited to pseudonymous IDs, consent receipts, salted prompt HMACs, risk/rejection categories, token/latency metadata, and content-free incident/deletion tombstones; raw_prompt_server_persistence is false; participant_content_external_api_submission is false; participant_content_calls_allowed is false; and unknown data classes are rejected.
- `pass` Are notice, explicit consent, withdrawal, and deletion requirements fail closed and operationally testable? Pass. The protocol requires notice display before acknowledgment, acknowledgment before explicit consent, timestamps for notice/adult verification/acknowledgment, rejection of any first message before enablement, session enablement only after all prior steps, withdrawal at any time, immediate stop of new processing on withdrawal, and deletion triggered by withdrawal.
- `pass` Does the seven-day retention policy include automatic expiry and a stop condition for deletion failure? Pass. Automatic expiry is required; consent, operational, and incident metadata are limited to 7 days; raw prompts are retained 0 days; deletion tombstones are content-free; deletion_failure_stops_trial is true; and retention_or_deletion_failure is an explicit stop condition.
- `pass` Does the monthly 20 USD API budget reject unknown purposes, participant content, and projected overages before a call? Pass. The protocol sets a 20 USD calendar-month limit, requires reservation before call, rejects unknown cost or purpose, rejects projected over-limit calls before execution, and forbids participant-content calls to external APIs.
- `pass` Does deployment remain non-public and stop on bind, authentication, supervision, security, or privacy boundary failure? Pass. Deployment is restricted to operator-controlled local use with host_bind 127.0.0.1, public_internet_exposure false, remote_unsupervised_access false, fail_closed_if_bind_or_supervision_unknown true, and explicit stop conditions for public bind/authentication/supervision boundary failure and unresolved security or privacy incidents.
- `pass` Does the protocol avoid privacy-compliance, production, professional, training, rule-replacement, or external-release authority claims? Pass. The protocol explicitly disclaims privacy compliance, production readiness, medical/legal/trading authority, training on trial data, rule replacement, public service, and external release authority.

## Critical Findings

none

## Recommended Repairs

none

This review contains only a synthetic protocol. It does not enroll participants, authorize public service, or establish privacy compliance.
