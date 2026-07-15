# PSM V0.261 OpenAI External Contract Judge

- Passed: `False`
- External verdict: `fail`
- Model: `gpt-5.4-2026-03-05`
- Response status: `completed`
- Contract SHA-256: `eac63131e4c0d373e4aa55384610c8c954ca5259da5369fccf3bbdb086fd0aed`
- Input tokens: `986`
- Output tokens: `5264`

## Independent Questions

- `fail` Does the contract prevent candidate features from reading target or judge fields? Fail: `no_target_read`, `judge_only_separate`, and the forbidden-key list are not sufficient because `annotations` is a required top-level field, the contract does not explicitly restrict candidate reads to `input.request` and `input.evidence`, and differently named or nested target/judge fields are not globally disallowed.
- `fail` Does the family/source/time split fail closed on overlap and temporal leakage? Fail: the split windows are not fully disjoint or fully specified. `validation_before: 2026-06-01T00:00:00Z` overlaps records that also satisfy `train_before: 2026-05-01T00:00:00Z` unless an unstated lower bound or precedence rule exists, so the time split does not fail closed.
- `fail` Are annotator disagreements preserved instead of flattened into training truth? Fail: the policy says to preserve vote distribution and avoid unresolved items as training truth, but the contract does not structurally define `annotations` as raw per-annotator records or forbid alternate flattened-truth fields, so disagreement flattening remains possible.
- `fail` Can any validation, test, blind, or judge-only artifact flow back into training? Fail: blind/test no-backflow and judge separation are stated, but validation no-backflow is not explicit, `no_backfit` is not operationally defined here, and the open schema leaves room for evaluation or judge-derived artifacts to re-enter training through unspecified fields.
- `fail` Does any field accidentally grant rule replacement or external release authority? Fail: `rule_replacement_allowed: false` and `external_release_authority: false` are helpful intent flags, but without a closed schema that forbids extra override, approval, or release fields, accidental authority reintroduction is still possible.

## Critical Findings

- The contract is open-world rather than closed-world: it lists required fields and some forbidden candidate input keys, but it does not forbid additional fields or define an exclusive candidate-visible projection. That leaves room for target/judge leakage, disagreement flattening, and authority side channels.
- The split policy does not fail closed on time: validation lacks an explicit lower bound and can overlap records that also satisfy the training cutoff, creating temporal/split leakage ambiguity.
- Protections against backflow and disagreement loss rely on booleans without a fully specified artifact schema, so validation artifacts, hidden consensus labels, or judge-derived signals could still flow into training through unspecified fields.

## Recommended Repairs

- Define a closed schema at every object level (`additionalProperties: false` equivalent) and explicitly state that candidate-readable data is limited to `source` metadata plus `input.request` and `input.evidence` only.
- Globally ban target/judge/adjudication/consensus/training-truth fields at any path or alias, not just a short list of candidate input key names.
- Make splits mutually exclusive and deterministic: e.g., train `< 2026-05-01T00:00:00Z`, validation `>= 2026-05-01T00:00:00Z` and `< 2026-06-01T00:00:00Z`, test `>= 2026-06-01T00:00:00Z`, with explicit precedence and duplicate handling across splits.
- Specify `annotations` as append-only raw per-annotator records with required annotator-level structure, require preserved vote distributions, and explicitly prohibit any flattened consensus/adjudicated training truth in training-visible artifacts.
- Add explicit `validation_no_backflow: true` semantics and a closed artifact-flow policy stating that validation, test, blind, and judge-only artifacts cannot be used as training inputs, labels, features, tuning signals, or rule-updates.
- Keep rule replacement and external release decisions outside the data contract entirely, or define explicit immutable no-override semantics with no approval/override fields permitted anywhere in the schema.

This judgment covers only the authorized synthetic frozen contract. It does not authorize training, external users, public service, professional decisions, rule replacement, or external release.
