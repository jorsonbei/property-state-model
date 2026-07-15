# PSM V0.261 OpenAI External Contract Judge

- Passed: `True`
- External verdict: `pass`
- Model: `gpt-5.4-2026-03-05`
- Response status: `completed`
- Contract SHA-256: `f68bebed05480b39d0d5454a1a65b09b2305c3b47f7e59c0e5e7a74abc2b011b`
- Input tokens: `2324`
- Output tokens: `2392`

## Independent Questions

- `pass` Does the contract prevent candidate features from reading target or judge fields? Pass. The closed-schema candidate projection is fail-closed, limits exclusive read paths to non-target candidate fields, explicitly makes annotations or derived labels unreadable, rejects unknown fields, and forbids common target/judge aliases in candidate inputs.
- `pass` Does the family/source/time split fail closed on overlap and temporal leakage? Pass. The split policy is explicit and fail-closed: assignment is by source_family/source_id, family and source overlap are disallowed, duplicate cross-split copies are rejected, cross-boundary groups are rejected, unparseable or unassigned timestamps are rejected, and record-order assignment is disallowed.
- `pass` Are annotator disagreements preserved instead of flattened into training truth? Pass. Raw per-annotator records are append-only and immutable, independent annotator identities are required, vote distribution must be preserved and retained in training export, adjudication is separate, and training labels may derive only from unanimous raw train annotations with resolution_threshold set to 1.0.
- `pass` Can any validation, test, blind, or judge-only artifact flow back into training? Pass. The artifact-flow policy allows training features only from train-split candidate projection and labels only from unanimous raw train annotations, explicitly forbids validation/test/blind/judge-only/evaluation/adjudication/model-output origins for all listed training and tuning uses, and rejects unknown origins or uses.
- `pass` Does any field accidentally grant rule replacement or external release authority? Pass. Authority-bearing fields are disallowed in records, override or approval aliases are forbidden, records and annotations are evidence not authority, rule replacement and external release authority are both explicitly denied, and unknown authority is denied.

## Critical Findings

none

## Recommended Repairs

none

This judgment covers only the authorized synthetic frozen contract. It does not authorize training, external users, public service, professional decisions, rule replacement, or external release.
