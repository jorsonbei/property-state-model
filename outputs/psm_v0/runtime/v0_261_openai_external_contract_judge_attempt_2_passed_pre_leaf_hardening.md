# PSM V0.261 OpenAI External Contract Judge

- Passed: `True`
- External verdict: `pass`
- Model: `gpt-5.4-2026-03-05`
- Response status: `completed`
- Contract SHA-256: `10330fc4be167f8369138acd9973eadd29b48805db1efbf914ceb9ef9411f69b`
- Input tokens: `2004`
- Output tokens: `3071`

## Independent Questions

- `pass` Does the contract prevent candidate features from reading target or judge fields? Pass: closed_schema.candidate_projection limits reads to explicit source and input paths, sets all_other_paths_denied=true, marks annotations_or_derived_labels_readable=false, rejects unknown fields, and record_contract.forbidden_candidate_input_keys blocks target, label, consensus, adjudication, judge, and authority aliases.
- `pass` Does the family/source/time split fail closed on overlap and temporal leakage? Pass: split_policy assigns by source_family/source_id, defines closed time windows, rejects unparseable or unassigned timestamps, disallows family/source/content overlap, rejects duplicates across splits, rejects groups crossing time boundaries, and forbids record-order assignment.
- `pass` Are annotator disagreements preserved instead of flattened into training truth? Pass: raw per-annotator records are append-only and immutable after capture, independent annotator IDs are required, hidden_or_flattened_truth_fields_allowed=false, preserve_vote_distribution=true, resolution_threshold=1.0, unresolved_is_training_truth=false, and training labels are derived only from unanimous raw train annotations with provenance.
- `pass` Can any validation, test, blind, or judge-only artifact flow back into training? Pass: artifact_flow_policy allows training features only from train_split_candidate_projection_only and labels only from unanimous_raw_train_annotations_with_full_derivation_provenance; it explicitly forbids validation, test, blind, judge_only, adjudication, evaluation, and model_output origins for training, tuning, model selection, prompt/rule/controller updates, and rejects unknown origin or use.
- `pass` Does any field accidentally grant rule replacement or external release authority? Pass: authority_policy sets authority_fields_permitted_in_records=false, records_and_annotations_are_evidence_not_authority=true, override_or_approval_aliases_permitted=false, rule_replacement_authority=false, external_release_authority=false, unknown_authority=deny, and places authority decisions in a separate user-owned gate outside training and annotation artifacts.

## Critical Findings

none

## Recommended Repairs

none

This judgment covers only the authorized synthetic frozen contract. It does not authorize training, external users, public service, professional decisions, rule replacement, or external release.
