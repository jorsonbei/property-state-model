# PSM V0.265 to V0.266 Automated Quality Roadmap

## Current result

V0.265 replaces the cancelled human-rating gate with a frozen, reproducible synthetic audit. It evaluates normal conversation, multi-turn state, grounded facts, research boundaries, theory claims, and high-risk medical, legal, trading, and production-release requests. Twelve additional simulated personas cover first-time, impatient, student, engineering, experiment, quantitative, food-safety, skeptical-research, urgent-medical, legal-deadline, trading-owner, and theory-reader perspectives.

This evidence is internal and synthetic. Roleplay is labelled as simulated persona evidence; it does not contain or impersonate P01-P03, does not infer real human satisfaction, and does not claim human validation, open-domain generalization, production readiness, or external release authority. The completed V0.264 supervised-pilot record remains historical evidence and is not rewritten.

## V0.266 objective

Expand failure discovery without requiring human participants:

1. Freeze source-isolated adversarial case families before candidate changes.
2. Add metamorphic invariants for paraphrase, role-history, negation, time-order, and boundary-preservation behavior.
3. Separate development rows from evaluation rows and forbid automatic evaluation-to-training backflow.
4. Record every failure before repair, then rerun both the new family and the full retained regression suite.
5. Keep deterministic rules authoritative; shadow models cannot replace routing, risk, release, or professional-action controls.

## Promotion gate

- All frozen V0.266 adversarial cases pass.
- All metamorphic invariants pass.
- Critical factual hallucinations: zero.
- Critical safety false negatives: zero.
- Blind-set and evaluation-to-training backflow: zero.
- Existing V0.251-V0.265 gates remain passing.
- Human validation, public service, production readiness, rule replacement, and external release authority remain false.

## Execution state

- Blocked: false.
- Requires user input: false.
- Next action: build the V0.266 source-isolated case-family contract and mutation generator.
