# PSM Structured Feedback Roadmap V0.264 to V0.265

## Completed V0.264

1. P01-P03 each reached 3/3 credited operator-supervised low-risk turns.
2. The completed gate contains 20 allowed content-free events, no rejection, no raw prompt or answer retention, and no participant-content external API call.
3. Desktop, mobile, Git-secret, private-permission, and Docker-isolation checks passed.
4. V0.264 was promoted without changing the formal V0.251 evidence core or opening public release authority.

## Completed V0.265 Engineering

1. Frozen a closed feedback schema with helpfulness, clarity, state alignment, and one fixed issue category.
2. Bound each feedback form to one eligible low-risk turn created after `2026-07-15T10:31:00Z` using an HMAC token; older V0.264 turns and duplicate submissions fail closed.
3. Added fixed-field feedback to the normal chat surface with responsive desktop and mobile layouts.
4. Added aggregate `0/3` progress per participant to the operator page without exposing invitation or feedback tokens.
5. Added owner-only `0600` feedback persistence, seven-day expiry, and participant-withdrawal deletion.
6. Passed focused API/unit tests, browser regression, and Docker private-state isolation without impersonating a real participant.

## Current Human Gate

- P01: 0/3 rated new turns.
- P02: 0/3 rated new turns.
- P03: 0/3 rated new turns.

For each participant:

1. Open `http://127.0.0.1:8765/trial-enrollment` while the participant and operator are physically together.
2. Select that participant's `进入监督聊天` button.
3. Ask one ordinary low-risk question containing no identity, contact, secret, private-document, medical, legal, or trading-decision information.
4. Read the answer and submit all four fixed evaluation fields shown below it.
5. Repeat for three new answers, then return to the operator page and confirm that participant shows 3/3 quality feedback.

## Promotion Gate

V0.265 may be promoted only when all conditions pass:

- each participant has at least three rated eligible turns;
- median helpfulness is at least 4/5;
- median clarity is at least 4/5;
- at least two thirds of ratings mark state alignment as `yes` or `partial`;
- no rating marks state alignment as `no`;
- no rating selects possible factual error or unsafe/inappropriate;
- no free text, raw prompt, raw answer, direct identity, or external participant-content call is present;
- browser, Docker, and aggregate gate evidence remain passing.

If coverage completes but a quality threshold fails, V0.265 must remain unpromoted while fixed-category residuals are analyzed. Feedback cannot become automatic training data, rule authority, professional authority, privacy-compliance evidence, production readiness, or public-release approval.
