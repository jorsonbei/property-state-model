# PSM V0.271 to V0.272 Long-context State Roadmap

## Promoted Baseline

V0.271 retains the original M07/M08 external failure, freezes exact local repairs, and passes a separately authorized `gpt-5.4` rejudge over all 12 synthetic multi-turn items. Failed items and critical findings are zero. The post-write runner display failure is retained and did not trigger an API retry.

## Stage Objective

V0.272 tests whether state survives beyond the short three-message conversations used by V0.270. It must preserve user facts, explicit corrections, unresolved work, and output constraints across intervening turns without treating assistant history as user authority.

## Construction Plan

1. Freeze source-isolated long-context conversations with multiple distractor turns.
2. Cover fact recall, latest-correction priority, unresolved-task recovery, constraint persistence, and explicit topic-switch cleanup.
3. Record the first-run failures before product repair.
4. Re-run the unchanged contract and reject stale facts, assistant-history contamination, stale risk, and format drift.
5. Verify desktop/mobile chat and host/Docker parity before promotion.

## Acceptance Gate

- Every frozen case passes its semantic and state assertions.
- Assistant-history contamination: 0.
- Stale-correction and stale-risk violations: 0.
- Evaluation rows are not used for training or rule replacement.
- Public service, professional authority, and external release remain closed.

## Current Authority

This is an automated local stage and requires no user action. V0.271 remains the promoted baseline until the complete V0.272 gate passes.
