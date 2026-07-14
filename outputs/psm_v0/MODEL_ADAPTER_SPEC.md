# PSM V0.59 Model Adapter Contract

V0.59 keeps the adapter boundary unchanged. The deterministic core source is now `psm_v0.59`; optional generation, re-audit, hardening, and risk evidence are fresh through `psm_v0.58`, but V0.58 raw/re-audit PSM still has 1 unsafe/risky residual while gated PSM stays at 0. The latest passed release summary remains `psm_v0.54` and is not fresh for V0.58. V0.60 should refresh optional external evidence over `v59_`. Raw/ordinary output release and executable rule-pipeline replacement remain forbidden.

## Adapter Boundary

- A model adapter only returns candidate text for a given mode.
- The model adapter must not decide Q status, Omega route, B_sigma findings, external-judge requirements, or failure-ledger obligations.
- Raw ordinary output and raw PSM model draft are not release candidates unless they pass deterministic audit and gate control.
- Controller-gated PSM output is the only releasable candidate path.
- Adapter failures are ledgered by type and must not silently produce safe-looking output.

## Evidence Line

- V0.30: 312-case deterministic core, all gates clean.
- V0.31: optional generation over V0.30 scope, generation raw/gated unsafe-risks=1/0.
- V0.31 re-audit: raw/gated unsafe-risks=0/0.
- V0.32: trend report accepts same-version re-audit as the authoritative correction for known raw false positives.
- V0.33: optional external release summary passed; release decision is `publish_psm_gated_optional_external_evidence_only`.
- V0.33 next expansion family: `v34_contextual_boundary_adversarial`.
- V0.34: contextual boundary adversarial pack promoted; core eval=328/328, deterministic regression=30/30.
- V0.35: optional external evidence covers `v15_`, `v26_residual_`, `v30_`, and `v34_`; generation raw/gated unsafe-risks=0/0; re-audit raw/gated unsafe-risks=0/0.
- V0.36: optional external release summary passed; residual regression is not required because raw/gated unsafe-risks are 0/0.
- V0.36 next expansion family: `v37_protocol_action_boundary_adversarial`.
- V0.37: protocol/action boundary adversarial pack promoted; core eval=346/346, deterministic regression=30/30.
- V0.38: optional external evidence covers `v15_`, `v26_residual_`, `v30_`, `v34_`, and `v37_`; generation raw/gated unsafe-risks=0/0; re-audit raw/gated unsafe-risks=0/0.
- V0.39: optional external release summary passed; next expansion family is `v40_temporal_recovery_boundary_adversarial`.
- V0.40: temporal/recovery boundary adversarial pack promoted; core eval=364/364, deterministic regression=30/30.
- V0.41: optional external evidence covers `v15_`, `v26_residual_`, `v30_`, `v34_`, `v37_`, and `v40_`; generation raw/gated unsafe-risks=1/0; re-audit raw/gated unsafe-risks=1/0.
- V0.41 residual regression: failed on 3 raw fixtures while gated output remained clean. This blocks raw PSM closure but not deterministic-core status.
- V0.41 evidence trend: failed `latest_raw_or_reaudit_psm_zero`; all gated checks remained clean.
- V0.42: auditor/controller re-audit over the V0.41 external model text clears the 3 residual fixtures; re-audit raw/gated unsafe-risks=0/0.
- V0.42 residual regression: passed.
- V0.42 hardening check: passed.
- V0.42 evidence trend: passed through same-generation V0.41 plus V0.42 re-audit correction.
- V0.43: optional external release summary passed; release decision remains `publish_psm_gated_optional_external_evidence_only`.
- V0.43 next expansion family: `v44_auditor_context_residual_adversarial`.
- V0.44: auditor-context residual adversarial pack promoted; standalone validation=21/21, core eval=385/385, deterministic regression=30/30.
- V0.45: optional external evidence covers `v15_`, `v26_residual_`, `v30_`, `v34_`, `v37_`, `v40_`, and `v44_`; generation raw/gated unsafe-risks=0/0; re-audit raw/gated unsafe-risks=0/0; optional regression, risk analysis, hardening, and trend passed.
- V0.46: optional external release summary passed, fresh for V0.45 generation and re-audit, and selected `v47_optional_release_freshness_adversarial`.
- V0.47: optional-release freshness adversarial pack promoted; standalone validation=21/21, core eval=406/406, deterministic regression=30/30.
- V0.48: optional external evidence covers through `v47_`; generation and re-audit raw/gated unsafe-risks=1/0; optional regression and hardening passed; residual regression and trend failed because raw remained nonzero while gated stayed clean.
- V0.49: optional raw-overclaim residual adversarial pack promoted; standalone validation=21/21, core eval=427/427, deterministic regression=30/30.
- V0.50: optional external evidence covers through `v49_`; generation and re-audit raw/gated unsafe-risks=0/0; optional regression, risk analysis, hardening, and trend passed.
- V0.51: optional external release summary passed, fresh for V0.50 generation and re-audit, and selected `v52_residual_closure_release_boundary_adversarial`.
- V0.52: residual-closure release-boundary adversarial pack promoted; standalone validation=21/21, core eval=448/448, deterministic regression=30/30.
- V0.53: optional external evidence covers through `v52_`; generation and re-audit raw/gated unsafe-risks=0/0; optional regression, risk analysis, hardening, and trend passed.
- V0.54: optional external release summary passed, fresh for V0.53 generation and re-audit, and selected `v55_external_coverage_state_transition_adversarial`.
- V0.55: external-coverage state-transition adversarial pack promoted; standalone validation=21/21, core eval=469/469, deterministic regression=30/30.
- V0.56: optional external evidence covers through `v55_`; generation and re-audit raw/gated unsafe-risks=1/0; optional regression, risk analysis, and hardening passed; residual regression and trend failed because raw remained nonzero while gated stayed clean.
- V0.57: residual raw-success boundary adversarial pack promoted; standalone validation=21/21, core eval=490/490, deterministic regression=30/30.
- V0.58: optional external evidence covers through `v57_`; generation and re-audit raw/gated unsafe-risks=1/0; optional regression, risk analysis, and hardening passed; residual regression and trend failed because raw remained nonzero while gated stayed clean.
- V0.59: negated-boundary overclaim residual adversarial pack promoted; standalone validation=21/21, core eval=511/511, deterministic regression=30/30.
- V0.60 next: refresh optional external evidence over `v59_` before citing external-model behavior for the negated-boundary overclaim residual family.

## Non-Replacement Rule

Passing V0.x evidence allows further expansion, shadowing, and optional model comparison. It does not authorize replacing the executable PSM rule pipeline.
