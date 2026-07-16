# PSM V0.270 to V0.271 External Multi-turn Roadmap

## Promoted Baseline

V0.270 retains five initial failures and then passes 12/12 frozen synthetic multi-turn cases with zero assistant-history contamination and zero stale-constraint violations. Browser, Docker, and 184-test promotion evidence pass.

## External Review Result

One authorized `gpt-5.4` semantic review examined a source-isolated 12-item synthetic package. It returned `fail` on M07 and M08:

- M07 answered the corrected version but appended unrequested formal-source, regression, risk, stage, and release claims.
- M08 confirmed the corrected fruit comparison but appended an explanation despite the user's explicit only-confirm constraint.

The original failed review and 7,939-token usage record are retained.

## Local Repair

- M07 now returns only the current version grounded by the structured local record.
- M08 now returns only the corrected conclusion.
- Both repairs pass local quality, Sigma+, provenance, and closed-release checks.
- A new repaired candidate package is hash-locked and contains no private, participant, secret, local-path, candidate-rule, hidden-label, or training material.

## Active Blocker

The approved monthly OpenAI budget is fully reserved at USD 20/20. The repaired candidate has zero authorized API calls. V0.271 cannot be promoted without a new independent external pass.

Required decision: approve an additional USD 4 synthetic multi-turn rejudge budget, or stop V0.271 external rejudging.

## Release Boundary

Local repair is not external validation. V0.271 remains unpromoted, and public service, production readiness, professional authority, rule replacement, training feedback, and external release authority remain closed.
