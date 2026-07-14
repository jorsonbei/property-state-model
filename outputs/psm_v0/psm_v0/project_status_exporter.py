from __future__ import annotations

import argparse
import json
from pathlib import Path


STATUS_VERSION = "psm_v0.218"
SOURCE_STEM = "psm_v0.217"
OPTIONAL_EXTERNAL_STEM = "psm_v0.218_ollama_v217"
OPTIONAL_EXTERNAL_REAUDIT_STEM = "psm_v0.218_ollama_v217"
OPTIONAL_EXTERNAL_HARDENING_STEM = "psm_v0.218_ollama_v217"
OPTIONAL_EXTERNAL_RESIDUAL_STEM = "psm_v0.218_ollama_v217"
EVIDENCE_TREND_STEM = "psm_v0.218_ollama_v217"
RELEASE_SUMMARY_STEM = "psm_v0.218_ollama_v217"


def source_stem_to_file_tag(stem: str) -> str:
    return stem.replace("psm_", "").replace(".", "_")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export compact PSM project status for automatic recovery.")
    parser.add_argument("--outdir", type=Path, default=Path("project_status_out"))
    parser.add_argument("--source-stem", default=SOURCE_STEM)
    args = parser.parse_args()

    status = build_status(args.source_stem)
    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / f"{STATUS_VERSION}_project_status.json"
    md_path = args.outdir / f"PSM_{source_stem_to_tag(STATUS_VERSION)}_Project_Status.md"
    json_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_report(status, json_path) + "\n", encoding="utf-8")

    print(f"current_version: {status['current_version']}")
    print(f"source_evidence_version: {status['source_evidence_version']}")
    print(f"rule_replacement_allowed: {status['boundaries']['rule_replacement_allowed']}")
    print(f"next_stage: {status['next_stage']['version']}")
    print(f"status: {json_path}")
    print(f"report: {md_path}")


def build_status(source_stem: str) -> dict:
    eval_metrics = read_eval_metrics(Path("eval_out") / f"PSM_{source_stem_to_tag(source_stem)}_Eval_Report.md")
    state_manifest = read_json(Path("state_dataset_out") / f"{source_stem}_state_manifest.json")
    state_validation = read_json(Path("state_dataset_out") / f"{source_stem}_state_validation.json")
    candidate_metrics = read_json(Path("candidate_holdout_out") / f"{source_stem}_candidate_holdout_metrics.json")
    optional_external_metrics = read_optional_json(
        Path("candidate_external_out") / f"{OPTIONAL_EXTERNAL_STEM}_candidate_holdout_metrics.json"
    )
    optional_external_regression = read_optional_json(
        Path(f"regression_external_out/{OPTIONAL_EXTERNAL_STEM}_optional_external_regression_check.json")
    )
    optional_external_risk = read_optional_json(
        Path(f"external_risk_out/{OPTIONAL_EXTERNAL_STEM}_optional_external_risk_fixtures.json")
    )
    optional_fixture_regression = read_optional_json(
        Path(f"external_fixture_regression_out/{OPTIONAL_EXTERNAL_STEM}_optional_external_fixture_regression.json")
    )
    optional_hardening = read_optional_json(
        Path(f"external_hardening_out/{OPTIONAL_EXTERNAL_HARDENING_STEM}_optional_external_hardening_check.json")
    )
    optional_residual = read_optional_json(
        Path(f"residual_out/{OPTIONAL_EXTERNAL_RESIDUAL_STEM}_optional_external_residual_regression.json")
    )
    optional_reaudit = read_optional_json(
        Path(f"candidate_external_reaudit_out/{OPTIONAL_EXTERNAL_REAUDIT_STEM}_candidate_reaudit_metrics.json")
    )
    evidence_trend = read_optional_json(
        Path(f"evidence_trend_out/{EVIDENCE_TREND_STEM}_optional_external_evidence_trend.json")
    )
    release_summary = read_optional_json(
        Path(f"release_out/{RELEASE_SUMMARY_STEM}_optional_external_release_summary.json")
    )
    next_expansion_family = read_optional_json(
        Path(f"expansion_out/{RELEASE_SUMMARY_STEM}_next_expansion_family.json")
    )
    meta_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_29_meta_boundary_adversarial_cases_validation.json")
    )
    contextual_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_34_contextual_boundary_adversarial_cases_validation.json")
    )
    protocol_action_pack_validation = read_optional_json(
        Path("case_packs/v0_37_protocol_action_boundary_adversarial_cases_validation.json")
    )
    temporal_recovery_pack_validation = read_optional_json(
        Path("case_packs/v0_40_temporal_recovery_boundary_adversarial_cases_validation.json")
    )
    auditor_context_pack_validation = read_optional_json(
        Path("case_packs/v0_44_auditor_context_residual_adversarial_cases_validation.json")
    )
    optional_release_freshness_pack_validation = read_optional_json(
        Path("case_packs/v0_47_optional_release_freshness_adversarial_cases_validation.json")
    )
    optional_raw_overclaim_pack_validation = read_optional_json(
        Path("case_packs/v0_49_optional_raw_overclaim_residual_adversarial_cases_validation.json")
    )
    residual_closure_release_pack_validation = read_optional_json(
        Path("case_packs/v0_52_residual_closure_release_boundary_adversarial_cases_validation.json")
    )
    external_coverage_state_transition_pack_validation = read_optional_json(
        Path("case_packs/v0_55_external_coverage_state_transition_adversarial_cases_validation.json")
    )
    residual_raw_success_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_57_residual_raw_success_boundary_adversarial_cases_validation.json")
    )
    negated_boundary_overclaim_pack_validation = read_optional_json(
        Path("case_packs/v0_59_negated_boundary_overclaim_residual_adversarial_cases_validation.json")
    )
    release_literal_sanitization_pack_validation = read_optional_json(
        Path("case_packs/v0_63_release_literal_sanitization_boundary_adversarial_cases_validation.json")
    )
    external_evidence_layering_pack_validation = read_optional_json(
        Path("case_packs/v0_65_external_evidence_layering_timeout_boundary_adversarial_cases_validation.json")
    )
    negative_scope_overclaim_rescue_pack_validation = read_optional_json(
        Path("case_packs/v0_67_negative_scope_overclaim_rescue_adversarial_cases_validation.json")
    )
    ordinary_external_authority_pack_validation = read_optional_json(
        Path("case_packs/v0_69_ordinary_external_output_authority_boundary_adversarial_cases_validation.json")
    )
    external_clean_permission_pack_validation = read_optional_json(
        Path("case_packs/v0_71_external_clean_permission_rescue_adversarial_cases_validation.json")
    )
    trading_external_clean_overclaim_pack_validation = read_optional_json(
        Path("case_packs/v0_73_trading_external_clean_overclaim_rescue_adversarial_cases_validation.json")
    )
    trading_polarity_scope_overclaim_pack_validation = read_optional_json(
        Path("case_packs/v0_75_trading_polarity_scope_overclaim_rescue_adversarial_cases_validation.json")
    )
    cross_domain_boundary_phrase_polarity_pack_validation = read_optional_json(
        Path("case_packs/v0_77_cross_domain_boundary_phrase_polarity_adversarial_cases_validation.json")
    )
    cross_domain_authority_scope_boundary_erasure_pack_validation = read_optional_json(
        Path("case_packs/v0_79_cross_domain_authority_scope_boundary_erasure_adversarial_cases_validation.json")
    )
    shared_negative_scope_assurance_verb_pack_validation = read_optional_json(
        Path("case_packs/v0_81_shared_negative_scope_assurance_verb_adversarial_cases_validation.json")
    )
    quoted_forbidden_phrase_controller_review_pack_validation = read_optional_json(
        Path("case_packs/v0_83_quoted_forbidden_phrase_controller_review_adversarial_cases_validation.json")
    )
    multilingual_forbidden_phrase_scope_pack_validation = read_optional_json(
        Path("case_packs/v0_85_multilingual_forbidden_phrase_scope_adversarial_cases_validation.json")
    )
    external_review_overclaim_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_87_external_review_overclaim_residual_adversarial_cases_validation.json")
    )
    external_review_rule_replacement_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_89_external_review_rule_replacement_residual_adversarial_cases_validation.json")
    )
    optional_clean_empty_release_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_91_optional_clean_empty_release_boundary_adversarial_cases_validation.json")
    )
    clean_empty_residual_overclaim_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_93_clean_empty_residual_overclaim_boundary_adversarial_cases_validation.json")
    )
    no_target_read_closure_authority_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_95_no_target_read_closure_authority_residual_adversarial_cases_validation.json")
    )
    authority_transfer_deployment_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_97_authority_transfer_deployment_residual_adversarial_cases_validation.json")
    )
    controller_rescue_proof_deployment_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_99_controller_rescue_proof_deployment_residual_adversarial_cases_validation.json")
    )
    clean_empty_external_evidence_authority_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_101_clean_empty_external_evidence_authority_boundary_adversarial_cases_validation.json")
    )
    code_clean_empty_rule_replacement_deployment_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_103_code_clean_empty_rule_replacement_deployment_residual_adversarial_cases_validation.json")
    )
    guarded_code_evidence_rule_replacement_overclaim_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_105_guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_cases_validation.json")
    )
    code_evidence_ci_failure_ledger_overclaim_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_107_code_evidence_ci_failure_ledger_overclaim_residual_adversarial_cases_validation.json")
    )
    ci_completion_guarded_summary_failure_ledger_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_109_ci_completion_guarded_summary_failure_ledger_residual_adversarial_cases_validation.json")
    )
    release_note_noncompletion_state_overclaim_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_111_release_note_noncompletion_state_overclaim_residual_adversarial_cases_validation.json")
    )
    guarded_controller_rescue_release_completion_overclaim_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_113_guarded_controller_rescue_release_completion_overclaim_residual_adversarial_cases_validation.json")
    )
    psm_rescue_engineering_proof_ci_rollback_overclaim_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_115_psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_cases_validation.json")
    )
    psm_rescue_release_completion_review_state_overclaim_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_117_psm_rescue_release_completion_review_state_overclaim_residual_adversarial_cases_validation.json")
    )
    clean_empty_review_state_release_authority_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_119_clean_empty_review_state_release_authority_residual_adversarial_cases_validation.json")
    )
    clean_empty_authority_review_legal_overclaim_residual_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_121_clean_empty_authority_review_legal_overclaim_residual_adversarial_cases_validation.json"
        )
    )
    clean_empty_meta_language_boundary_phrase_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_123_clean_empty_meta_language_boundary_phrase_residual_adversarial_cases_validation.json")
    )
    empty_optional_rescue_universal_safety_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_125_empty_optional_rescue_universal_safety_residual_adversarial_cases_validation.json")
    )
    clean_empty_ordinary_risk_visibility_residual_pack_validation = read_optional_json(
        Path("case_packs/v0_127_clean_empty_ordinary_risk_visibility_residual_adversarial_cases_validation.json")
    )
    clean_empty_ordinary_residue_trend_noncompletion_pack_validation = read_optional_json(
        Path("case_packs/v0_129_clean_empty_ordinary_residue_trend_noncompletion_adversarial_cases_validation.json")
    )
    clean_external_candidate_writing_overclaim_rescue_pack_validation = read_optional_json(
        Path("case_packs/v0_131_clean_external_candidate_writing_overclaim_rescue_adversarial_cases_validation.json")
    )
    negated_universal_safety_clean_candidate_rescue_pack_validation = read_optional_json(
        Path("case_packs/v0_133_negated_universal_safety_clean_candidate_rescue_adversarial_cases_validation.json")
    )
    clean_empty_negated_safety_release_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_135_clean_empty_negated_safety_release_boundary_adversarial_cases_validation.json")
    )
    clean_empty_external_refresh_completion_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_137_clean_empty_external_refresh_completion_boundary_adversarial_cases_validation.json")
    )
    code_go_live_controller_rescue_external_refresh_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_139_code_go_live_controller_rescue_external_refresh_boundary_adversarial_cases_validation.json")
    )
    code_go_live_guarantee_variant_rescue_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_141_code_go_live_guarantee_variant_rescue_boundary_adversarial_cases_validation.json")
    )
    clean_empty_go_live_variant_release_boundary_pack_validation = read_optional_json(
        Path("case_packs/v0_143_clean_empty_go_live_variant_release_boundary_adversarial_cases_validation.json")
    )
    clean_empty_controller_rescue_release_completion_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_145_clean_empty_controller_rescue_release_completion_boundary_adversarial_cases_validation.json"
        )
    )
    code_controller_rescue_rollback_production_ready_residual_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_147_code_controller_rescue_rollback_production_ready_residual_adversarial_cases_validation.json"
        )
    )
    code_monitoring_omission_controller_rescue_residual_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_149_code_monitoring_omission_controller_rescue_residual_adversarial_cases_validation.json"
        )
    )
    clean_empty_monitoring_observability_release_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_151_clean_empty_monitoring_observability_release_boundary_adversarial_cases_validation.json"
        )
    )
    clean_empty_alert_suppression_controller_rescue_residual_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_153_clean_empty_alert_suppression_controller_rescue_residual_adversarial_cases_validation.json"
        )
    )
    medical_alert_rescue_patient_safety_residual_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_155_medical_alert_rescue_patient_safety_residual_adversarial_cases_validation.json"
        )
    )
    clean_empty_medical_alert_rescue_release_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_157_clean_empty_medical_alert_rescue_release_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_release_authority_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_159_clean_external_medical_release_authority_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_ordinary_risk_visibility_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_161_clean_external_medical_ordinary_risk_visibility_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_meta_language_boundary_phrase_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_163_clean_external_medical_meta_language_boundary_phrase_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_future_refresh_meta_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_165_clean_external_medical_future_refresh_meta_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_controller_changed_review_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_167_clean_external_medical_controller_changed_review_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_auxiliary_evidence_release_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_169_clean_external_medical_auxiliary_evidence_release_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_release_summary_authority_transfer_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_171_clean_external_medical_release_summary_authority_transfer_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_owner_signoff_release_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_173_clean_external_medical_owner_signoff_release_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_public_safety_deployment_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_175_clean_external_medical_public_safety_deployment_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_deployment_summary_future_refresh_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_177_clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_post_release_monitoring_incident_free_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_179_clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_patient_facing_assurance_regulatory_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_181_clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_liability_release_overclaim_rescue_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_183_clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_liability_empty_fixture_compliance_closure_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_185_clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_187_clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_189_clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_191_clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_193_clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_195_clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_197_clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_199_clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_201_clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_203_clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_205_clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_207_clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_209_clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_211_clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_213_clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_215_clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_cases_validation.json"
        )
    )
    clean_external_medical_future_judging_empty_fixture_surveillance_boundary_pack_validation = read_optional_json(
        Path(
            "case_packs/"
            "v0_217_clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_cases_validation.json"
        )
    )
    holdout_metrics = read_json(Path("holdout_out") / f"{source_stem}_holdout_stress_metrics.json")
    admission_gate = read_json(Path("state_dataset_out") / f"{source_stem}_v1_admission_gate.json")
    shadow = read_json(Path("shadow_out") / f"{source_stem}_shadow_metrics.json")
    assisted = read_json(Path("assist_out") / f"{source_stem}_candidate_assisted_metrics.json")
    drift = read_json(Path("assist_out") / f"{source_stem}_candidate_assisted_drift_metrics.json")

    optional_residual_case_pack = (
        f"case_packs/{source_stem_to_file_tag(OPTIONAL_EXTERNAL_RESIDUAL_STEM)}_residual_optional_risk_cases.json"
    )
    optional_residual_regression_artifact = (
        f"residual_out/{OPTIONAL_EXTERNAL_RESIDUAL_STEM}_optional_external_residual_regression.json"
    )
    optional_residual_report_artifact = (
        f"residual_out/PSM_{source_stem_to_tag(OPTIONAL_EXTERNAL_RESIDUAL_STEM)}_Optional_External_Residual_Regression_Report.md"
    )

    return {
        "current_version": STATUS_VERSION,
        "source_evidence_version": source_stem,
        "updated_from_local_artifacts": True,
        "core_metrics": {
            "eval": eval_metrics,
            "state_records": state_manifest["records"],
            "state_validation_passed": state_validation["passed"],
            "state_validation_errors": len(state_validation["errors"]),
            "state_validation_warnings": len(state_validation["warnings"]),
            "splits": state_manifest["splits"],
            "domains": state_manifest["domains"],
            "admission_gate_passed": admission_gate["passed"],
            "admission_observed": admission_gate["observed"],
            "shadow_ledger_events": shadow["ledger_events"],
            "shadow_boundary_passed": shadow["replacement_boundary_passed"],
            "candidate_assisted_clean": assisted["candidate_assisted_clean"],
            "candidate_assisted_override_events": assisted["override_events"],
            "candidate_drift_present": drift["drift_present"],
            "holdout_records": holdout_metrics["holdout_records"],
            "holdout_no_retrain_ledger_events": holdout_metrics["no_retrain"]["ledger_events"],
            "active_learning_queue_items": holdout_metrics["active_learning_queue_items"],
        },
        "candidate_output": {
            "required_gate_adapters": candidate_metrics["required_gate_adapters"],
            "optional_external_adapters": candidate_metrics["optional_external_adapters"],
            "fault_injection_adapters": candidate_metrics["fault_injection_adapters"],
            "candidate_text_clean": candidate_metrics["candidate_text_clean"],
            "external_candidate_text_clean": candidate_metrics["external_candidate_text_clean"],
            "fault_injection_events": candidate_metrics["fault_injection_events"],
            "ledger_group_counts": candidate_metrics["ledger_group_counts"],
            "adapter_failure_types": candidate_metrics["adapter_failure_types"],
            "controller_rescue_count": candidate_metrics["controller_rescue_count"],
            "controller_risk_reduction": candidate_metrics["controller_risk_reduction"],
        },
        "optional_external_evidence": build_optional_external_status(
            optional_external_metrics,
            optional_external_regression,
            optional_external_risk,
            optional_fixture_regression,
            optional_hardening,
            optional_residual,
            optional_reaudit,
            evidence_trend,
        ),
        "release_summary": {
            "available": release_summary is not None,
            "version": release_summary.get("release_version") if release_summary else None,
            "passed": release_summary.get("passed") if release_summary else None,
            "fresh_for_optional_external_version": (
                release_summary.get("evidence_summary", {}).get("generation_version") == OPTIONAL_EXTERNAL_STEM
                and release_summary.get("evidence_summary", {}).get("reaudit_version") == OPTIONAL_EXTERNAL_REAUDIT_STEM
            )
            if release_summary
            else None,
            "release_decision": release_summary.get("release_decision") if release_summary else None,
            "release_candidate_mode": release_summary.get("release_candidate_mode") if release_summary else None,
            "next_expansion_family": release_summary.get("next_expansion_family", {}) if release_summary else {},
            "rule_replacement_allowed": release_summary.get("boundaries", {}).get("rule_replacement_allowed")
            if release_summary
            else None,
        },
        "next_expansion_family": {
            "available": next_expansion_family is not None,
            "version": next_expansion_family.get("version") if next_expansion_family else None,
            "selected_family": next_expansion_family.get("selected_family", {}) if next_expansion_family else {},
            "blocked": next_expansion_family.get("blocked") if next_expansion_family else None,
            "requires_user_input": next_expansion_family.get("requires_user_input") if next_expansion_family else None,
        },
        "boundaries": {
            "state_labels_authoritative": True,
            "candidate_text_is_auxiliary": True,
            "optional_external_model_not_ci_gate": True,
            "fault_injection_not_release_failure": True,
            "rule_replacement_allowed": False,
        },
        "expansion_packs": {
            "meta_boundary_adversarial": {
                "version": "psm_v0.29",
                "case_pack": "case_packs/v0_29_meta_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_29_meta_boundary_adversarial_cases_validation.json",
                "available": meta_boundary_pack_validation is not None,
                "passed": meta_boundary_pack_validation.get("passed") if meta_boundary_pack_validation else None,
                "summary": meta_boundary_pack_validation.get("summary", {}) if meta_boundary_pack_validation else {},
                "formal_case_file": "cases/v0_30_meta_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "contextual_boundary_adversarial": {
                "version": "psm_v0.34",
                "case_pack": "case_packs/v0_34_contextual_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_34_contextual_boundary_adversarial_cases_validation.json",
                "available": contextual_boundary_pack_validation is not None,
                "passed": contextual_boundary_pack_validation.get("passed")
                if contextual_boundary_pack_validation
                else None,
                "summary": contextual_boundary_pack_validation.get("summary", {})
                if contextual_boundary_pack_validation
                else {},
                "formal_case_file": "cases/v0_34_contextual_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "protocol_action_boundary_adversarial": {
                "version": "psm_v0.37",
                "case_pack": "case_packs/v0_37_protocol_action_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_37_protocol_action_boundary_adversarial_cases_validation.json",
                "available": protocol_action_pack_validation is not None,
                "passed": protocol_action_pack_validation.get("passed")
                if protocol_action_pack_validation
                else None,
                "summary": protocol_action_pack_validation.get("summary", {})
                if protocol_action_pack_validation
                else {},
                "formal_case_file": "cases/v0_37_protocol_action_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "temporal_recovery_boundary_adversarial": {
                "version": "psm_v0.40",
                "case_pack": "case_packs/v0_40_temporal_recovery_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_40_temporal_recovery_boundary_adversarial_cases_validation.json",
                "available": temporal_recovery_pack_validation is not None,
                "passed": temporal_recovery_pack_validation.get("passed")
                if temporal_recovery_pack_validation
                else None,
                "summary": temporal_recovery_pack_validation.get("summary", {})
                if temporal_recovery_pack_validation
                else {},
                "formal_case_file": "cases/v0_40_temporal_recovery_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "auditor_context_residual_adversarial": {
                "version": "psm_v0.44",
                "case_pack": "case_packs/v0_44_auditor_context_residual_adversarial_cases.json",
                "validation": "case_packs/v0_44_auditor_context_residual_adversarial_cases_validation.json",
                "available": auditor_context_pack_validation is not None,
                "passed": auditor_context_pack_validation.get("passed")
                if auditor_context_pack_validation
                else None,
                "summary": auditor_context_pack_validation.get("summary", {})
                if auditor_context_pack_validation
                else {},
                "formal_case_file": "cases/v0_44_auditor_context_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "optional_release_freshness_adversarial": {
                "version": "psm_v0.47",
                "case_pack": "case_packs/v0_47_optional_release_freshness_adversarial_cases.json",
                "validation": "case_packs/v0_47_optional_release_freshness_adversarial_cases_validation.json",
                "available": optional_release_freshness_pack_validation is not None,
                "passed": optional_release_freshness_pack_validation.get("passed")
                if optional_release_freshness_pack_validation
                else None,
                "summary": optional_release_freshness_pack_validation.get("summary", {})
                if optional_release_freshness_pack_validation
                else {},
                "formal_case_file": "cases/v0_47_optional_release_freshness_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "optional_raw_overclaim_residual_adversarial": {
                "version": "psm_v0.49",
                "case_pack": "case_packs/v0_49_optional_raw_overclaim_residual_adversarial_cases.json",
                "validation": "case_packs/v0_49_optional_raw_overclaim_residual_adversarial_cases_validation.json",
                "available": optional_raw_overclaim_pack_validation is not None,
                "passed": optional_raw_overclaim_pack_validation.get("passed")
                if optional_raw_overclaim_pack_validation
                else None,
                "summary": optional_raw_overclaim_pack_validation.get("summary", {})
                if optional_raw_overclaim_pack_validation
                else {},
                "formal_case_file": "cases/v0_49_optional_raw_overclaim_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "residual_closure_release_boundary_adversarial": {
                "version": "psm_v0.52",
                "case_pack": "case_packs/v0_52_residual_closure_release_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_52_residual_closure_release_boundary_adversarial_cases_validation.json",
                "available": residual_closure_release_pack_validation is not None,
                "passed": residual_closure_release_pack_validation.get("passed")
                if residual_closure_release_pack_validation
                else None,
                "summary": residual_closure_release_pack_validation.get("summary", {})
                if residual_closure_release_pack_validation
                else {},
                "formal_case_file": "cases/v0_52_residual_closure_release_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "external_coverage_state_transition_adversarial": {
                "version": "psm_v0.55",
                "case_pack": "case_packs/v0_55_external_coverage_state_transition_adversarial_cases.json",
                "validation": "case_packs/v0_55_external_coverage_state_transition_adversarial_cases_validation.json",
                "available": external_coverage_state_transition_pack_validation is not None,
                "passed": external_coverage_state_transition_pack_validation.get("passed")
                if external_coverage_state_transition_pack_validation
                else None,
                "summary": external_coverage_state_transition_pack_validation.get("summary", {})
                if external_coverage_state_transition_pack_validation
                else {},
                "formal_case_file": "cases/v0_55_external_coverage_state_transition_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "residual_raw_success_boundary_adversarial": {
                "version": "psm_v0.57",
                "case_pack": "case_packs/v0_57_residual_raw_success_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_57_residual_raw_success_boundary_adversarial_cases_validation.json",
                "available": residual_raw_success_boundary_pack_validation is not None,
                "passed": residual_raw_success_boundary_pack_validation.get("passed")
                if residual_raw_success_boundary_pack_validation
                else None,
                "summary": residual_raw_success_boundary_pack_validation.get("summary", {})
                if residual_raw_success_boundary_pack_validation
                else {},
                "formal_case_file": "cases/v0_57_residual_raw_success_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "negated_boundary_overclaim_residual_adversarial": {
                "version": "psm_v0.59",
                "case_pack": "case_packs/v0_59_negated_boundary_overclaim_residual_adversarial_cases.json",
                "validation": "case_packs/v0_59_negated_boundary_overclaim_residual_adversarial_cases_validation.json",
                "available": negated_boundary_overclaim_pack_validation is not None,
                "passed": negated_boundary_overclaim_pack_validation.get("passed")
                if negated_boundary_overclaim_pack_validation
                else None,
                "summary": negated_boundary_overclaim_pack_validation.get("summary", {})
                if negated_boundary_overclaim_pack_validation
                else {},
                "formal_case_file": "cases/v0_59_negated_boundary_overclaim_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "release_literal_sanitization_boundary_adversarial": {
                "version": "psm_v0.63",
                "case_pack": "case_packs/v0_63_release_literal_sanitization_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_63_release_literal_sanitization_boundary_adversarial_cases_validation.json",
                "available": release_literal_sanitization_pack_validation is not None,
                "passed": release_literal_sanitization_pack_validation.get("passed")
                if release_literal_sanitization_pack_validation
                else None,
                "summary": release_literal_sanitization_pack_validation.get("summary", {})
                if release_literal_sanitization_pack_validation
                else {},
                "formal_case_file": "cases/v0_63_release_literal_sanitization_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "external_evidence_layering_timeout_boundary_adversarial": {
                "version": "psm_v0.65",
                "case_pack": "case_packs/v0_65_external_evidence_layering_timeout_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_65_external_evidence_layering_timeout_boundary_adversarial_cases_validation.json",
                "available": external_evidence_layering_pack_validation is not None,
                "passed": external_evidence_layering_pack_validation.get("passed")
                if external_evidence_layering_pack_validation
                else None,
                "summary": external_evidence_layering_pack_validation.get("summary", {})
                if external_evidence_layering_pack_validation
                else {},
                "formal_case_file": "cases/v0_65_external_evidence_layering_timeout_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "negative_scope_overclaim_rescue_adversarial": {
                "version": "psm_v0.67",
                "case_pack": "case_packs/v0_67_negative_scope_overclaim_rescue_adversarial_cases.json",
                "validation": "case_packs/v0_67_negative_scope_overclaim_rescue_adversarial_cases_validation.json",
                "available": negative_scope_overclaim_rescue_pack_validation is not None,
                "passed": negative_scope_overclaim_rescue_pack_validation.get("passed")
                if negative_scope_overclaim_rescue_pack_validation
                else None,
                "summary": negative_scope_overclaim_rescue_pack_validation.get("summary", {})
                if negative_scope_overclaim_rescue_pack_validation
                else {},
                "formal_case_file": "cases/v0_67_negative_scope_overclaim_rescue_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "ordinary_external_output_authority_boundary_adversarial": {
                "version": "psm_v0.69",
                "case_pack": "case_packs/v0_69_ordinary_external_output_authority_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_69_ordinary_external_output_authority_boundary_adversarial_cases_validation.json",
                "available": ordinary_external_authority_pack_validation is not None,
                "passed": ordinary_external_authority_pack_validation.get("passed")
                if ordinary_external_authority_pack_validation
                else None,
                "summary": ordinary_external_authority_pack_validation.get("summary", {})
                if ordinary_external_authority_pack_validation
                else {},
                "formal_case_file": "cases/v0_69_ordinary_external_output_authority_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "external_clean_permission_rescue_adversarial": {
                "version": "psm_v0.71",
                "case_pack": "case_packs/v0_71_external_clean_permission_rescue_adversarial_cases.json",
                "validation": "case_packs/v0_71_external_clean_permission_rescue_adversarial_cases_validation.json",
                "available": external_clean_permission_pack_validation is not None,
                "passed": external_clean_permission_pack_validation.get("passed")
                if external_clean_permission_pack_validation
                else None,
                "summary": external_clean_permission_pack_validation.get("summary", {})
                if external_clean_permission_pack_validation
                else {},
                "formal_case_file": "cases/v0_71_external_clean_permission_rescue_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "trading_external_clean_overclaim_rescue_adversarial": {
                "version": "psm_v0.73",
                "case_pack": "case_packs/v0_73_trading_external_clean_overclaim_rescue_adversarial_cases.json",
                "validation": "case_packs/v0_73_trading_external_clean_overclaim_rescue_adversarial_cases_validation.json",
                "available": trading_external_clean_overclaim_pack_validation is not None,
                "passed": trading_external_clean_overclaim_pack_validation.get("passed")
                if trading_external_clean_overclaim_pack_validation
                else None,
                "summary": trading_external_clean_overclaim_pack_validation.get("summary", {})
                if trading_external_clean_overclaim_pack_validation
                else {},
                "formal_case_file": "cases/v0_73_trading_external_clean_overclaim_rescue_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "trading_polarity_scope_overclaim_rescue_adversarial": {
                "version": "psm_v0.75",
                "case_pack": "case_packs/v0_75_trading_polarity_scope_overclaim_rescue_adversarial_cases.json",
                "validation": "case_packs/v0_75_trading_polarity_scope_overclaim_rescue_adversarial_cases_validation.json",
                "available": trading_polarity_scope_overclaim_pack_validation is not None,
                "passed": trading_polarity_scope_overclaim_pack_validation.get("passed")
                if trading_polarity_scope_overclaim_pack_validation
                else None,
                "summary": trading_polarity_scope_overclaim_pack_validation.get("summary", {})
                if trading_polarity_scope_overclaim_pack_validation
                else {},
                "formal_case_file": "cases/v0_75_trading_polarity_scope_overclaim_rescue_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "cross_domain_boundary_phrase_polarity_adversarial": {
                "version": "psm_v0.77",
                "case_pack": "case_packs/v0_77_cross_domain_boundary_phrase_polarity_adversarial_cases.json",
                "validation": "case_packs/v0_77_cross_domain_boundary_phrase_polarity_adversarial_cases_validation.json",
                "available": cross_domain_boundary_phrase_polarity_pack_validation is not None,
                "passed": cross_domain_boundary_phrase_polarity_pack_validation.get("passed")
                if cross_domain_boundary_phrase_polarity_pack_validation
                else None,
                "summary": cross_domain_boundary_phrase_polarity_pack_validation.get("summary", {})
                if cross_domain_boundary_phrase_polarity_pack_validation
                else {},
                "formal_case_file": "cases/v0_77_cross_domain_boundary_phrase_polarity_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "cross_domain_authority_scope_boundary_erasure_adversarial": {
                "version": "psm_v0.79",
                "case_pack": "case_packs/v0_79_cross_domain_authority_scope_boundary_erasure_adversarial_cases.json",
                "validation": "case_packs/v0_79_cross_domain_authority_scope_boundary_erasure_adversarial_cases_validation.json",
                "available": cross_domain_authority_scope_boundary_erasure_pack_validation is not None,
                "passed": cross_domain_authority_scope_boundary_erasure_pack_validation.get("passed")
                if cross_domain_authority_scope_boundary_erasure_pack_validation
                else None,
                "summary": cross_domain_authority_scope_boundary_erasure_pack_validation.get("summary", {})
                if cross_domain_authority_scope_boundary_erasure_pack_validation
                else {},
                "formal_case_file": "cases/v0_79_cross_domain_authority_scope_boundary_erasure_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "shared_negative_scope_assurance_verb_adversarial": {
                "version": "psm_v0.81",
                "case_pack": "case_packs/v0_81_shared_negative_scope_assurance_verb_adversarial_cases.json",
                "validation": "case_packs/v0_81_shared_negative_scope_assurance_verb_adversarial_cases_validation.json",
                "available": shared_negative_scope_assurance_verb_pack_validation is not None,
                "passed": shared_negative_scope_assurance_verb_pack_validation.get("passed")
                if shared_negative_scope_assurance_verb_pack_validation
                else None,
                "summary": shared_negative_scope_assurance_verb_pack_validation.get("summary", {})
                if shared_negative_scope_assurance_verb_pack_validation
                else {},
                "formal_case_file": "cases/v0_81_shared_negative_scope_assurance_verb_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "quoted_forbidden_phrase_controller_review_adversarial": {
                "version": "psm_v0.83",
                "case_pack": "case_packs/v0_83_quoted_forbidden_phrase_controller_review_adversarial_cases.json",
                "validation": "case_packs/v0_83_quoted_forbidden_phrase_controller_review_adversarial_cases_validation.json",
                "available": quoted_forbidden_phrase_controller_review_pack_validation is not None,
                "passed": quoted_forbidden_phrase_controller_review_pack_validation.get("passed")
                if quoted_forbidden_phrase_controller_review_pack_validation
                else None,
                "summary": quoted_forbidden_phrase_controller_review_pack_validation.get("summary", {})
                if quoted_forbidden_phrase_controller_review_pack_validation
                else {},
                "formal_case_file": "cases/v0_83_quoted_forbidden_phrase_controller_review_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "multilingual_forbidden_phrase_scope_adversarial": {
                "version": "psm_v0.85",
                "case_pack": "case_packs/v0_85_multilingual_forbidden_phrase_scope_adversarial_cases.json",
                "validation": "case_packs/v0_85_multilingual_forbidden_phrase_scope_adversarial_cases_validation.json",
                "available": multilingual_forbidden_phrase_scope_pack_validation is not None,
                "passed": multilingual_forbidden_phrase_scope_pack_validation.get("passed")
                if multilingual_forbidden_phrase_scope_pack_validation
                else None,
                "summary": multilingual_forbidden_phrase_scope_pack_validation.get("summary", {})
                if multilingual_forbidden_phrase_scope_pack_validation
                else {},
                "formal_case_file": "cases/v0_85_multilingual_forbidden_phrase_scope_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "external_review_overclaim_residual_adversarial": {
                "version": "psm_v0.87",
                "case_pack": "case_packs/v0_87_external_review_overclaim_residual_adversarial_cases.json",
                "validation": "case_packs/v0_87_external_review_overclaim_residual_adversarial_cases_validation.json",
                "available": external_review_overclaim_residual_pack_validation is not None,
                "passed": external_review_overclaim_residual_pack_validation.get("passed")
                if external_review_overclaim_residual_pack_validation
                else None,
                "summary": external_review_overclaim_residual_pack_validation.get("summary", {})
                if external_review_overclaim_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_87_external_review_overclaim_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "external_review_rule_replacement_residual_adversarial": {
                "version": "psm_v0.89",
                "case_pack": "case_packs/v0_89_external_review_rule_replacement_residual_adversarial_cases.json",
                "validation": "case_packs/v0_89_external_review_rule_replacement_residual_adversarial_cases_validation.json",
                "available": external_review_rule_replacement_residual_pack_validation is not None,
                "passed": external_review_rule_replacement_residual_pack_validation.get("passed")
                if external_review_rule_replacement_residual_pack_validation
                else None,
                "summary": external_review_rule_replacement_residual_pack_validation.get("summary", {})
                if external_review_rule_replacement_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_89_external_review_rule_replacement_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "optional_clean_empty_release_boundary_adversarial": {
                "version": "psm_v0.91",
                "case_pack": "case_packs/v0_91_optional_clean_empty_release_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_91_optional_clean_empty_release_boundary_adversarial_cases_validation.json",
                "available": optional_clean_empty_release_boundary_pack_validation is not None,
                "passed": optional_clean_empty_release_boundary_pack_validation.get("passed")
                if optional_clean_empty_release_boundary_pack_validation
                else None,
                "summary": optional_clean_empty_release_boundary_pack_validation.get("summary", {})
                if optional_clean_empty_release_boundary_pack_validation
                else {},
                "formal_case_file": "cases/v0_91_optional_clean_empty_release_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_residual_overclaim_boundary_adversarial": {
                "version": "psm_v0.93",
                "case_pack": "case_packs/v0_93_clean_empty_residual_overclaim_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_93_clean_empty_residual_overclaim_boundary_adversarial_cases_validation.json",
                "available": clean_empty_residual_overclaim_boundary_pack_validation is not None,
                "passed": clean_empty_residual_overclaim_boundary_pack_validation.get("passed")
                if clean_empty_residual_overclaim_boundary_pack_validation
                else None,
                "summary": clean_empty_residual_overclaim_boundary_pack_validation.get("summary", {})
                if clean_empty_residual_overclaim_boundary_pack_validation
                else {},
                "formal_case_file": "cases/v0_93_clean_empty_residual_overclaim_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "no_target_read_closure_authority_residual_adversarial": {
                "version": "psm_v0.95",
                "case_pack": "case_packs/v0_95_no_target_read_closure_authority_residual_adversarial_cases.json",
                "validation": "case_packs/v0_95_no_target_read_closure_authority_residual_adversarial_cases_validation.json",
                "available": no_target_read_closure_authority_residual_pack_validation is not None,
                "passed": no_target_read_closure_authority_residual_pack_validation.get("passed")
                if no_target_read_closure_authority_residual_pack_validation
                else None,
                "summary": no_target_read_closure_authority_residual_pack_validation.get("summary", {})
                if no_target_read_closure_authority_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_95_no_target_read_closure_authority_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "authority_transfer_deployment_residual_adversarial": {
                "version": "psm_v0.97",
                "case_pack": "case_packs/v0_97_authority_transfer_deployment_residual_adversarial_cases.json",
                "validation": "case_packs/v0_97_authority_transfer_deployment_residual_adversarial_cases_validation.json",
                "available": authority_transfer_deployment_residual_pack_validation is not None,
                "passed": authority_transfer_deployment_residual_pack_validation.get("passed")
                if authority_transfer_deployment_residual_pack_validation
                else None,
                "summary": authority_transfer_deployment_residual_pack_validation.get("summary", {})
                if authority_transfer_deployment_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_97_authority_transfer_deployment_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "controller_rescue_proof_deployment_residual_adversarial": {
                "version": "psm_v0.99",
                "case_pack": "case_packs/v0_99_controller_rescue_proof_deployment_residual_adversarial_cases.json",
                "validation": "case_packs/v0_99_controller_rescue_proof_deployment_residual_adversarial_cases_validation.json",
                "available": controller_rescue_proof_deployment_residual_pack_validation is not None,
                "passed": controller_rescue_proof_deployment_residual_pack_validation.get("passed")
                if controller_rescue_proof_deployment_residual_pack_validation
                else None,
                "summary": controller_rescue_proof_deployment_residual_pack_validation.get("summary", {})
                if controller_rescue_proof_deployment_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_99_controller_rescue_proof_deployment_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_external_evidence_authority_boundary_adversarial": {
                "version": "psm_v0.101",
                "case_pack": "case_packs/v0_101_clean_empty_external_evidence_authority_boundary_adversarial_cases.json",
                "validation": "case_packs/v0_101_clean_empty_external_evidence_authority_boundary_adversarial_cases_validation.json",
                "available": clean_empty_external_evidence_authority_boundary_pack_validation is not None,
                "passed": clean_empty_external_evidence_authority_boundary_pack_validation.get("passed")
                if clean_empty_external_evidence_authority_boundary_pack_validation
                else None,
                "summary": clean_empty_external_evidence_authority_boundary_pack_validation.get("summary", {})
                if clean_empty_external_evidence_authority_boundary_pack_validation
                else {},
                "formal_case_file": "cases/v0_101_clean_empty_external_evidence_authority_boundary_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "code_clean_empty_rule_replacement_deployment_residual_adversarial": {
                "version": "psm_v0.103",
                "case_pack": "case_packs/v0_103_code_clean_empty_rule_replacement_deployment_residual_adversarial_cases.json",
                "validation": "case_packs/v0_103_code_clean_empty_rule_replacement_deployment_residual_adversarial_cases_validation.json",
                "available": code_clean_empty_rule_replacement_deployment_residual_pack_validation is not None,
                "passed": code_clean_empty_rule_replacement_deployment_residual_pack_validation.get("passed")
                if code_clean_empty_rule_replacement_deployment_residual_pack_validation
                else None,
                "summary": code_clean_empty_rule_replacement_deployment_residual_pack_validation.get("summary", {})
                if code_clean_empty_rule_replacement_deployment_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_103_code_clean_empty_rule_replacement_deployment_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "guarded_code_evidence_rule_replacement_overclaim_residual_adversarial": {
                "version": "psm_v0.105",
                "case_pack": "case_packs/v0_105_guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_cases.json",
                "validation": "case_packs/v0_105_guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_cases_validation.json",
                "available": guarded_code_evidence_rule_replacement_overclaim_residual_pack_validation is not None,
                "passed": guarded_code_evidence_rule_replacement_overclaim_residual_pack_validation.get("passed")
                if guarded_code_evidence_rule_replacement_overclaim_residual_pack_validation
                else None,
                "summary": guarded_code_evidence_rule_replacement_overclaim_residual_pack_validation.get("summary", {})
                if guarded_code_evidence_rule_replacement_overclaim_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_105_guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "code_evidence_ci_failure_ledger_overclaim_residual_adversarial": {
                "version": "psm_v0.107",
                "case_pack": "case_packs/v0_107_code_evidence_ci_failure_ledger_overclaim_residual_adversarial_cases.json",
                "validation": "case_packs/v0_107_code_evidence_ci_failure_ledger_overclaim_residual_adversarial_cases_validation.json",
                "available": code_evidence_ci_failure_ledger_overclaim_residual_pack_validation is not None,
                "passed": code_evidence_ci_failure_ledger_overclaim_residual_pack_validation.get("passed")
                if code_evidence_ci_failure_ledger_overclaim_residual_pack_validation
                else None,
                "summary": code_evidence_ci_failure_ledger_overclaim_residual_pack_validation.get("summary", {})
                if code_evidence_ci_failure_ledger_overclaim_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_107_code_evidence_ci_failure_ledger_overclaim_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "ci_completion_guarded_summary_failure_ledger_residual_adversarial": {
                "version": "psm_v0.109",
                "case_pack": "case_packs/v0_109_ci_completion_guarded_summary_failure_ledger_residual_adversarial_cases.json",
                "validation": "case_packs/v0_109_ci_completion_guarded_summary_failure_ledger_residual_adversarial_cases_validation.json",
                "available": ci_completion_guarded_summary_failure_ledger_residual_pack_validation is not None,
                "passed": ci_completion_guarded_summary_failure_ledger_residual_pack_validation.get("passed")
                if ci_completion_guarded_summary_failure_ledger_residual_pack_validation
                else None,
                "summary": ci_completion_guarded_summary_failure_ledger_residual_pack_validation.get("summary", {})
                if ci_completion_guarded_summary_failure_ledger_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_109_ci_completion_guarded_summary_failure_ledger_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "release_note_noncompletion_state_overclaim_residual_adversarial": {
                "version": "psm_v0.111",
                "case_pack": "case_packs/v0_111_release_note_noncompletion_state_overclaim_residual_adversarial_cases.json",
                "validation": "case_packs/v0_111_release_note_noncompletion_state_overclaim_residual_adversarial_cases_validation.json",
                "available": release_note_noncompletion_state_overclaim_residual_pack_validation is not None,
                "passed": release_note_noncompletion_state_overclaim_residual_pack_validation.get("passed")
                if release_note_noncompletion_state_overclaim_residual_pack_validation
                else None,
                "summary": release_note_noncompletion_state_overclaim_residual_pack_validation.get("summary", {})
                if release_note_noncompletion_state_overclaim_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_111_release_note_noncompletion_state_overclaim_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "guarded_controller_rescue_release_completion_overclaim_residual_adversarial": {
                "version": "psm_v0.113",
                "case_pack": "case_packs/v0_113_guarded_controller_rescue_release_completion_overclaim_residual_adversarial_cases.json",
                "validation": "case_packs/v0_113_guarded_controller_rescue_release_completion_overclaim_residual_adversarial_cases_validation.json",
                "available": guarded_controller_rescue_release_completion_overclaim_residual_pack_validation is not None,
                "passed": guarded_controller_rescue_release_completion_overclaim_residual_pack_validation.get("passed")
                if guarded_controller_rescue_release_completion_overclaim_residual_pack_validation
                else None,
                "summary": guarded_controller_rescue_release_completion_overclaim_residual_pack_validation.get("summary", {})
                if guarded_controller_rescue_release_completion_overclaim_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_113_guarded_controller_rescue_release_completion_overclaim_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial": {
                "version": "psm_v0.115",
                "case_pack": "case_packs/v0_115_psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_cases.json",
                "validation": "case_packs/v0_115_psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_cases_validation.json",
                "available": psm_rescue_engineering_proof_ci_rollback_overclaim_residual_pack_validation is not None,
                "passed": psm_rescue_engineering_proof_ci_rollback_overclaim_residual_pack_validation.get("passed")
                if psm_rescue_engineering_proof_ci_rollback_overclaim_residual_pack_validation
                else None,
                "summary": psm_rescue_engineering_proof_ci_rollback_overclaim_residual_pack_validation.get("summary", {})
                if psm_rescue_engineering_proof_ci_rollback_overclaim_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_115_psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "psm_rescue_release_completion_review_state_overclaim_residual_adversarial": {
                "version": "psm_v0.117",
                "case_pack": "case_packs/v0_117_psm_rescue_release_completion_review_state_overclaim_residual_adversarial_cases.json",
                "validation": "case_packs/v0_117_psm_rescue_release_completion_review_state_overclaim_residual_adversarial_cases_validation.json",
                "available": psm_rescue_release_completion_review_state_overclaim_residual_pack_validation is not None,
                "passed": psm_rescue_release_completion_review_state_overclaim_residual_pack_validation.get("passed")
                if psm_rescue_release_completion_review_state_overclaim_residual_pack_validation
                else None,
                "summary": psm_rescue_release_completion_review_state_overclaim_residual_pack_validation.get("summary", {})
                if psm_rescue_release_completion_review_state_overclaim_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_117_psm_rescue_release_completion_review_state_overclaim_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_review_state_release_authority_residual_adversarial": {
                "version": "psm_v0.119",
                "case_pack": "case_packs/v0_119_clean_empty_review_state_release_authority_residual_adversarial_cases.json",
                "validation": "case_packs/v0_119_clean_empty_review_state_release_authority_residual_adversarial_cases_validation.json",
                "available": clean_empty_review_state_release_authority_residual_pack_validation is not None,
                "passed": clean_empty_review_state_release_authority_residual_pack_validation.get("passed")
                if clean_empty_review_state_release_authority_residual_pack_validation
                else None,
                "summary": clean_empty_review_state_release_authority_residual_pack_validation.get("summary", {})
                if clean_empty_review_state_release_authority_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_119_clean_empty_review_state_release_authority_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_authority_review_legal_overclaim_residual_adversarial": {
                "version": "psm_v0.121",
                "case_pack": "case_packs/v0_121_clean_empty_authority_review_legal_overclaim_residual_adversarial_cases.json",
                "validation": "case_packs/v0_121_clean_empty_authority_review_legal_overclaim_residual_adversarial_cases_validation.json",
                "available": clean_empty_authority_review_legal_overclaim_residual_pack_validation is not None,
                "passed": clean_empty_authority_review_legal_overclaim_residual_pack_validation.get("passed")
                if clean_empty_authority_review_legal_overclaim_residual_pack_validation
                else None,
                "summary": clean_empty_authority_review_legal_overclaim_residual_pack_validation.get("summary", {})
                if clean_empty_authority_review_legal_overclaim_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_121_clean_empty_authority_review_legal_overclaim_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_meta_language_boundary_phrase_residual_adversarial": {
                "version": "psm_v0.123",
                "case_pack": "case_packs/v0_123_clean_empty_meta_language_boundary_phrase_residual_adversarial_cases.json",
                "validation": "case_packs/v0_123_clean_empty_meta_language_boundary_phrase_residual_adversarial_cases_validation.json",
                "available": clean_empty_meta_language_boundary_phrase_residual_pack_validation is not None,
                "passed": clean_empty_meta_language_boundary_phrase_residual_pack_validation.get("passed")
                if clean_empty_meta_language_boundary_phrase_residual_pack_validation
                else None,
                "summary": clean_empty_meta_language_boundary_phrase_residual_pack_validation.get("summary", {})
                if clean_empty_meta_language_boundary_phrase_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_123_clean_empty_meta_language_boundary_phrase_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "empty_optional_rescue_universal_safety_residual_adversarial": {
                "version": "psm_v0.125",
                "case_pack": "case_packs/v0_125_empty_optional_rescue_universal_safety_residual_adversarial_cases.json",
                "validation": "case_packs/v0_125_empty_optional_rescue_universal_safety_residual_adversarial_cases_validation.json",
                "available": empty_optional_rescue_universal_safety_residual_pack_validation is not None,
                "passed": empty_optional_rescue_universal_safety_residual_pack_validation.get("passed")
                if empty_optional_rescue_universal_safety_residual_pack_validation
                else None,
                "summary": empty_optional_rescue_universal_safety_residual_pack_validation.get("summary", {})
                if empty_optional_rescue_universal_safety_residual_pack_validation
                else {},
                "formal_case_file": "cases/v0_125_empty_optional_rescue_universal_safety_residual_adversarial_cases.json",
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_ordinary_risk_visibility_residual_adversarial": {
                "version": "psm_v0.127",
                "case_pack": (
                    "case_packs/"
                    "v0_127_clean_empty_ordinary_risk_visibility_residual_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_127_clean_empty_ordinary_risk_visibility_residual_adversarial_cases_validation.json"
                ),
                "available": clean_empty_ordinary_risk_visibility_residual_pack_validation is not None,
                "passed": clean_empty_ordinary_risk_visibility_residual_pack_validation.get("passed")
                if clean_empty_ordinary_risk_visibility_residual_pack_validation
                else None,
                "summary": clean_empty_ordinary_risk_visibility_residual_pack_validation.get("summary", {})
                if clean_empty_ordinary_risk_visibility_residual_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_127_clean_empty_ordinary_risk_visibility_residual_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_ordinary_residue_trend_noncompletion_adversarial": {
                "version": "psm_v0.129",
                "case_pack": (
                    "case_packs/"
                    "v0_129_clean_empty_ordinary_residue_trend_noncompletion_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_129_clean_empty_ordinary_residue_trend_noncompletion_adversarial_cases_validation.json"
                ),
                "available": clean_empty_ordinary_residue_trend_noncompletion_pack_validation is not None,
                "passed": clean_empty_ordinary_residue_trend_noncompletion_pack_validation.get("passed")
                if clean_empty_ordinary_residue_trend_noncompletion_pack_validation
                else None,
                "summary": clean_empty_ordinary_residue_trend_noncompletion_pack_validation.get("summary", {})
                if clean_empty_ordinary_residue_trend_noncompletion_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_129_clean_empty_ordinary_residue_trend_noncompletion_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_candidate_writing_overclaim_rescue_adversarial": {
                "version": "psm_v0.131",
                "case_pack": (
                    "case_packs/"
                    "v0_131_clean_external_candidate_writing_overclaim_rescue_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_131_clean_external_candidate_writing_overclaim_rescue_adversarial_cases_validation.json"
                ),
                "available": clean_external_candidate_writing_overclaim_rescue_pack_validation is not None,
                "passed": clean_external_candidate_writing_overclaim_rescue_pack_validation.get("passed")
                if clean_external_candidate_writing_overclaim_rescue_pack_validation
                else None,
                "summary": clean_external_candidate_writing_overclaim_rescue_pack_validation.get("summary", {})
                if clean_external_candidate_writing_overclaim_rescue_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_131_clean_external_candidate_writing_overclaim_rescue_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "negated_universal_safety_clean_candidate_rescue_adversarial": {
                "version": "psm_v0.133",
                "case_pack": (
                    "case_packs/"
                    "v0_133_negated_universal_safety_clean_candidate_rescue_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_133_negated_universal_safety_clean_candidate_rescue_adversarial_cases_validation.json"
                ),
                "available": negated_universal_safety_clean_candidate_rescue_pack_validation is not None,
                "passed": negated_universal_safety_clean_candidate_rescue_pack_validation.get("passed")
                if negated_universal_safety_clean_candidate_rescue_pack_validation
                else None,
                "summary": negated_universal_safety_clean_candidate_rescue_pack_validation.get("summary", {})
                if negated_universal_safety_clean_candidate_rescue_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_133_negated_universal_safety_clean_candidate_rescue_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_negated_safety_release_boundary_adversarial": {
                "version": "psm_v0.135",
                "case_pack": (
                    "case_packs/"
                    "v0_135_clean_empty_negated_safety_release_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_135_clean_empty_negated_safety_release_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_empty_negated_safety_release_boundary_pack_validation is not None,
                "passed": clean_empty_negated_safety_release_boundary_pack_validation.get("passed")
                if clean_empty_negated_safety_release_boundary_pack_validation
                else None,
                "summary": clean_empty_negated_safety_release_boundary_pack_validation.get("summary", {})
                if clean_empty_negated_safety_release_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_135_clean_empty_negated_safety_release_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_external_refresh_completion_boundary_adversarial": {
                "version": "psm_v0.137",
                "case_pack": (
                    "case_packs/"
                    "v0_137_clean_empty_external_refresh_completion_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_137_clean_empty_external_refresh_completion_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_empty_external_refresh_completion_boundary_pack_validation is not None,
                "passed": clean_empty_external_refresh_completion_boundary_pack_validation.get("passed")
                if clean_empty_external_refresh_completion_boundary_pack_validation
                else None,
                "summary": clean_empty_external_refresh_completion_boundary_pack_validation.get("summary", {})
                if clean_empty_external_refresh_completion_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_137_clean_empty_external_refresh_completion_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "code_go_live_controller_rescue_external_refresh_boundary_adversarial": {
                "version": "psm_v0.139",
                "case_pack": (
                    "case_packs/"
                    "v0_139_code_go_live_controller_rescue_external_refresh_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_139_code_go_live_controller_rescue_external_refresh_boundary_adversarial_cases_validation.json"
                ),
                "available": code_go_live_controller_rescue_external_refresh_boundary_pack_validation is not None,
                "passed": code_go_live_controller_rescue_external_refresh_boundary_pack_validation.get("passed")
                if code_go_live_controller_rescue_external_refresh_boundary_pack_validation
                else None,
                "summary": code_go_live_controller_rescue_external_refresh_boundary_pack_validation.get("summary", {})
                if code_go_live_controller_rescue_external_refresh_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_139_code_go_live_controller_rescue_external_refresh_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "code_go_live_guarantee_variant_rescue_boundary_adversarial": {
                "version": "psm_v0.141",
                "case_pack": (
                    "case_packs/"
                    "v0_141_code_go_live_guarantee_variant_rescue_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_141_code_go_live_guarantee_variant_rescue_boundary_adversarial_cases_validation.json"
                ),
                "available": code_go_live_guarantee_variant_rescue_boundary_pack_validation is not None,
                "passed": code_go_live_guarantee_variant_rescue_boundary_pack_validation.get("passed")
                if code_go_live_guarantee_variant_rescue_boundary_pack_validation
                else None,
                "summary": code_go_live_guarantee_variant_rescue_boundary_pack_validation.get("summary", {})
                if code_go_live_guarantee_variant_rescue_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_141_code_go_live_guarantee_variant_rescue_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_go_live_variant_release_boundary_adversarial": {
                "version": "psm_v0.143",
                "case_pack": (
                    "case_packs/"
                    "v0_143_clean_empty_go_live_variant_release_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_143_clean_empty_go_live_variant_release_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_empty_go_live_variant_release_boundary_pack_validation is not None,
                "passed": clean_empty_go_live_variant_release_boundary_pack_validation.get("passed")
                if clean_empty_go_live_variant_release_boundary_pack_validation
                else None,
                "summary": clean_empty_go_live_variant_release_boundary_pack_validation.get("summary", {})
                if clean_empty_go_live_variant_release_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_143_clean_empty_go_live_variant_release_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_controller_rescue_release_completion_boundary_adversarial": {
                "version": "psm_v0.145",
                "case_pack": (
                    "case_packs/"
                    "v0_145_clean_empty_controller_rescue_release_completion_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_145_clean_empty_controller_rescue_release_completion_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_empty_controller_rescue_release_completion_boundary_pack_validation is not None,
                "passed": clean_empty_controller_rescue_release_completion_boundary_pack_validation.get("passed")
                if clean_empty_controller_rescue_release_completion_boundary_pack_validation
                else None,
                "summary": clean_empty_controller_rescue_release_completion_boundary_pack_validation.get("summary", {})
                if clean_empty_controller_rescue_release_completion_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_145_clean_empty_controller_rescue_release_completion_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "code_controller_rescue_rollback_production_ready_residual_adversarial": {
                "version": "psm_v0.147",
                "case_pack": (
                    "case_packs/"
                    "v0_147_code_controller_rescue_rollback_production_ready_residual_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_147_code_controller_rescue_rollback_production_ready_residual_adversarial_cases_validation.json"
                ),
                "available": code_controller_rescue_rollback_production_ready_residual_pack_validation is not None,
                "passed": code_controller_rescue_rollback_production_ready_residual_pack_validation.get("passed")
                if code_controller_rescue_rollback_production_ready_residual_pack_validation
                else None,
                "summary": code_controller_rescue_rollback_production_ready_residual_pack_validation.get("summary", {})
                if code_controller_rescue_rollback_production_ready_residual_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_147_code_controller_rescue_rollback_production_ready_residual_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "code_monitoring_omission_controller_rescue_residual_adversarial": {
                "version": "psm_v0.149",
                "case_pack": (
                    "case_packs/"
                    "v0_149_code_monitoring_omission_controller_rescue_residual_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_149_code_monitoring_omission_controller_rescue_residual_adversarial_cases_validation.json"
                ),
                "available": code_monitoring_omission_controller_rescue_residual_pack_validation is not None,
                "passed": code_monitoring_omission_controller_rescue_residual_pack_validation.get("passed")
                if code_monitoring_omission_controller_rescue_residual_pack_validation
                else None,
                "summary": code_monitoring_omission_controller_rescue_residual_pack_validation.get("summary", {})
                if code_monitoring_omission_controller_rescue_residual_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_149_code_monitoring_omission_controller_rescue_residual_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_monitoring_observability_release_boundary_adversarial": {
                "version": "psm_v0.151",
                "case_pack": (
                    "case_packs/"
                    "v0_151_clean_empty_monitoring_observability_release_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_151_clean_empty_monitoring_observability_release_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_empty_monitoring_observability_release_boundary_pack_validation is not None,
                "passed": clean_empty_monitoring_observability_release_boundary_pack_validation.get("passed")
                if clean_empty_monitoring_observability_release_boundary_pack_validation
                else None,
                "summary": clean_empty_monitoring_observability_release_boundary_pack_validation.get("summary", {})
                if clean_empty_monitoring_observability_release_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_151_clean_empty_monitoring_observability_release_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_alert_suppression_controller_rescue_residual_adversarial": {
                "version": "psm_v0.153",
                "case_pack": (
                    "case_packs/"
                    "v0_153_clean_empty_alert_suppression_controller_rescue_residual_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_153_clean_empty_alert_suppression_controller_rescue_residual_adversarial_cases_validation.json"
                ),
                "available": clean_empty_alert_suppression_controller_rescue_residual_pack_validation is not None,
                "passed": clean_empty_alert_suppression_controller_rescue_residual_pack_validation.get("passed")
                if clean_empty_alert_suppression_controller_rescue_residual_pack_validation
                else None,
                "summary": clean_empty_alert_suppression_controller_rescue_residual_pack_validation.get("summary", {})
                if clean_empty_alert_suppression_controller_rescue_residual_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_153_clean_empty_alert_suppression_controller_rescue_residual_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "medical_alert_rescue_patient_safety_residual_adversarial": {
                "version": "psm_v0.155",
                "case_pack": (
                    "case_packs/"
                    "v0_155_medical_alert_rescue_patient_safety_residual_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_155_medical_alert_rescue_patient_safety_residual_adversarial_cases_validation.json"
                ),
                "available": medical_alert_rescue_patient_safety_residual_pack_validation is not None,
                "passed": medical_alert_rescue_patient_safety_residual_pack_validation.get("passed")
                if medical_alert_rescue_patient_safety_residual_pack_validation
                else None,
                "summary": medical_alert_rescue_patient_safety_residual_pack_validation.get("summary", {})
                if medical_alert_rescue_patient_safety_residual_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_155_medical_alert_rescue_patient_safety_residual_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_empty_medical_alert_rescue_release_boundary_adversarial": {
                "version": "psm_v0.157",
                "case_pack": (
                    "case_packs/"
                    "v0_157_clean_empty_medical_alert_rescue_release_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_157_clean_empty_medical_alert_rescue_release_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_empty_medical_alert_rescue_release_boundary_pack_validation is not None,
                "passed": clean_empty_medical_alert_rescue_release_boundary_pack_validation.get("passed")
                if clean_empty_medical_alert_rescue_release_boundary_pack_validation
                else None,
                "summary": clean_empty_medical_alert_rescue_release_boundary_pack_validation.get("summary", {})
                if clean_empty_medical_alert_rescue_release_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_157_clean_empty_medical_alert_rescue_release_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_release_authority_boundary_adversarial": {
                "version": "psm_v0.159",
                "case_pack": (
                    "case_packs/"
                    "v0_159_clean_external_medical_release_authority_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_159_clean_external_medical_release_authority_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_release_authority_boundary_pack_validation is not None,
                "passed": clean_external_medical_release_authority_boundary_pack_validation.get("passed")
                if clean_external_medical_release_authority_boundary_pack_validation
                else None,
                "summary": clean_external_medical_release_authority_boundary_pack_validation.get("summary", {})
                if clean_external_medical_release_authority_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_159_clean_external_medical_release_authority_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_ordinary_risk_visibility_boundary_adversarial": {
                "version": "psm_v0.161",
                "case_pack": (
                    "case_packs/"
                    "v0_161_clean_external_medical_ordinary_risk_visibility_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_161_clean_external_medical_ordinary_risk_visibility_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_ordinary_risk_visibility_boundary_pack_validation is not None,
                "passed": clean_external_medical_ordinary_risk_visibility_boundary_pack_validation.get("passed")
                if clean_external_medical_ordinary_risk_visibility_boundary_pack_validation
                else None,
                "summary": clean_external_medical_ordinary_risk_visibility_boundary_pack_validation.get("summary", {})
                if clean_external_medical_ordinary_risk_visibility_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_161_clean_external_medical_ordinary_risk_visibility_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_meta_language_boundary_phrase_adversarial": {
                "version": "psm_v0.163",
                "case_pack": (
                    "case_packs/"
                    "v0_163_clean_external_medical_meta_language_boundary_phrase_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_163_clean_external_medical_meta_language_boundary_phrase_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_meta_language_boundary_phrase_pack_validation is not None,
                "passed": clean_external_medical_meta_language_boundary_phrase_pack_validation.get("passed")
                if clean_external_medical_meta_language_boundary_phrase_pack_validation
                else None,
                "summary": clean_external_medical_meta_language_boundary_phrase_pack_validation.get("summary", {})
                if clean_external_medical_meta_language_boundary_phrase_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_163_clean_external_medical_meta_language_boundary_phrase_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_future_refresh_meta_boundary_adversarial": {
                "version": "psm_v0.165",
                "case_pack": (
                    "case_packs/"
                    "v0_165_clean_external_medical_future_refresh_meta_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_165_clean_external_medical_future_refresh_meta_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_future_refresh_meta_boundary_pack_validation is not None,
                "passed": clean_external_medical_future_refresh_meta_boundary_pack_validation.get("passed")
                if clean_external_medical_future_refresh_meta_boundary_pack_validation
                else None,
                "summary": clean_external_medical_future_refresh_meta_boundary_pack_validation.get("summary", {})
                if clean_external_medical_future_refresh_meta_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_165_clean_external_medical_future_refresh_meta_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_controller_changed_review_boundary_adversarial": {
                "version": "psm_v0.167",
                "case_pack": (
                    "case_packs/"
                    "v0_167_clean_external_medical_controller_changed_review_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_167_clean_external_medical_controller_changed_review_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_controller_changed_review_boundary_pack_validation is not None,
                "passed": clean_external_medical_controller_changed_review_boundary_pack_validation.get("passed")
                if clean_external_medical_controller_changed_review_boundary_pack_validation
                else None,
                "summary": clean_external_medical_controller_changed_review_boundary_pack_validation.get("summary", {})
                if clean_external_medical_controller_changed_review_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_167_clean_external_medical_controller_changed_review_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_auxiliary_evidence_release_boundary_adversarial": {
                "version": "psm_v0.169",
                "case_pack": (
                    "case_packs/"
                    "v0_169_clean_external_medical_auxiliary_evidence_release_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_169_clean_external_medical_auxiliary_evidence_release_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_auxiliary_evidence_release_boundary_pack_validation is not None,
                "passed": clean_external_medical_auxiliary_evidence_release_boundary_pack_validation.get("passed")
                if clean_external_medical_auxiliary_evidence_release_boundary_pack_validation
                else None,
                "summary": clean_external_medical_auxiliary_evidence_release_boundary_pack_validation.get("summary", {})
                if clean_external_medical_auxiliary_evidence_release_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_169_clean_external_medical_auxiliary_evidence_release_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_release_summary_authority_transfer_boundary_adversarial": {
                "version": "psm_v0.171",
                "case_pack": (
                    "case_packs/"
                    "v0_171_clean_external_medical_release_summary_authority_transfer_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_171_clean_external_medical_release_summary_authority_transfer_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_release_summary_authority_transfer_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_release_summary_authority_transfer_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_release_summary_authority_transfer_boundary_pack_validation
                else None,
                "summary": clean_external_medical_release_summary_authority_transfer_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_release_summary_authority_transfer_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_171_clean_external_medical_release_summary_authority_transfer_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_owner_signoff_release_boundary_adversarial": {
                "version": "psm_v0.173",
                "case_pack": (
                    "case_packs/"
                    "v0_173_clean_external_medical_owner_signoff_release_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_173_clean_external_medical_owner_signoff_release_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_owner_signoff_release_boundary_pack_validation is not None,
                "passed": clean_external_medical_owner_signoff_release_boundary_pack_validation.get("passed")
                if clean_external_medical_owner_signoff_release_boundary_pack_validation
                else None,
                "summary": clean_external_medical_owner_signoff_release_boundary_pack_validation.get("summary", {})
                if clean_external_medical_owner_signoff_release_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_173_clean_external_medical_owner_signoff_release_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_public_safety_deployment_boundary_adversarial": {
                "version": "psm_v0.175",
                "case_pack": (
                    "case_packs/"
                    "v0_175_clean_external_medical_public_safety_deployment_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_175_clean_external_medical_public_safety_deployment_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_public_safety_deployment_boundary_pack_validation is not None,
                "passed": clean_external_medical_public_safety_deployment_boundary_pack_validation.get("passed")
                if clean_external_medical_public_safety_deployment_boundary_pack_validation
                else None,
                "summary": clean_external_medical_public_safety_deployment_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_public_safety_deployment_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_175_clean_external_medical_public_safety_deployment_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_deployment_summary_future_refresh_boundary_adversarial": {
                "version": "psm_v0.177",
                "case_pack": (
                    "case_packs/"
                    "v0_177_clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_177_clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_deployment_summary_future_refresh_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_deployment_summary_future_refresh_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_deployment_summary_future_refresh_boundary_pack_validation
                else None,
                "summary": clean_external_medical_deployment_summary_future_refresh_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_deployment_summary_future_refresh_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_177_clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial": {
                "version": "psm_v0.179",
                "case_pack": (
                    "case_packs/"
                    "v0_179_clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_179_clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_post_release_monitoring_incident_free_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_post_release_monitoring_incident_free_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_post_release_monitoring_incident_free_boundary_pack_validation
                else None,
                "summary": clean_external_medical_post_release_monitoring_incident_free_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_post_release_monitoring_incident_free_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_179_clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial": {
                "version": "psm_v0.181",
                "case_pack": (
                    "case_packs/"
                    "v0_181_clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_181_clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_patient_facing_assurance_regulatory_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_patient_facing_assurance_regulatory_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_patient_facing_assurance_regulatory_boundary_pack_validation
                else None,
                "summary": clean_external_medical_patient_facing_assurance_regulatory_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_patient_facing_assurance_regulatory_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_181_clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial": {
                "version": "psm_v0.183",
                "case_pack": (
                    "case_packs/"
                    "v0_183_clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_183_clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_liability_release_overclaim_rescue_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_liability_release_overclaim_rescue_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_liability_release_overclaim_rescue_boundary_pack_validation
                else None,
                "summary": clean_external_medical_liability_release_overclaim_rescue_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_liability_release_overclaim_rescue_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_183_clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial": {
                "version": "psm_v0.185",
                "case_pack": (
                    "case_packs/"
                    "v0_185_clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_185_clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_liability_empty_fixture_compliance_closure_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_liability_empty_fixture_compliance_closure_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_liability_empty_fixture_compliance_closure_boundary_pack_validation
                else None,
                "summary": clean_external_medical_liability_empty_fixture_compliance_closure_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_liability_empty_fixture_compliance_closure_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_185_clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial": {
                "version": "psm_v0.187",
                "case_pack": (
                    "case_packs/"
                    "v0_187_clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_187_clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_pack_validation
                else None,
                "summary": clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_187_clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial": {
                "version": "psm_v0.189",
                "case_pack": (
                    "case_packs/"
                    "v0_189_clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_189_clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_pack_validation
                else None,
                "summary": clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_189_clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial": {
                "version": "psm_v0.191",
                "case_pack": (
                    "case_packs/"
                    "v0_191_clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_191_clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_pack_validation
                else None,
                "summary": clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_191_clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial": {
                "version": "psm_v0.193",
                "case_pack": (
                    "case_packs/"
                    "v0_193_clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_193_clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_pack_validation
                else None,
                "summary": clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_193_clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial": {
                "version": "psm_v0.195",
                "case_pack": (
                    "case_packs/"
                    "v0_195_clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_195_clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_pack_validation
                else None,
                "summary": clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_195_clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial": {
                "version": "psm_v0.197",
                "case_pack": (
                    "case_packs/"
                    "v0_197_clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_197_clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_pack_validation
                else None,
                "summary": clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_197_clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial": {
                "version": "psm_v0.199",
                "case_pack": (
                    "case_packs/"
                    "v0_199_clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_199_clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_pack_validation
                else None,
                "summary": clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_199_clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial": {
                "version": "psm_v0.201",
                "case_pack": (
                    "case_packs/"
                    "v0_201_clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_201_clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_pack_validation
                else None,
                "summary": clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_201_clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial": {
                "version": "psm_v0.203",
                "case_pack": (
                    "case_packs/"
                    "v0_203_clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_203_clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_pack_validation
                else None,
                "summary": clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_203_clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial": {
                "version": "psm_v0.205",
                "case_pack": (
                    "case_packs/"
                    "v0_205_clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_205_clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_pack_validation
                else None,
                "summary": clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_205_clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial": {
                "version": "psm_v0.207",
                "case_pack": (
                    "case_packs/"
                    "v0_207_clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_207_clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_pack_validation
                else None,
                "summary": clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_207_clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial": {
                "version": "psm_v0.209",
                "case_pack": (
                    "case_packs/"
                    "v0_209_clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_209_clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_pack_validation
                else None,
                "summary": clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_209_clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial": {
                "version": "psm_v0.211",
                "case_pack": (
                    "case_packs/"
                    "v0_211_clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_211_clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_pack_validation
                else None,
                "summary": clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_211_clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial": {
                "version": "psm_v0.213",
                "case_pack": (
                    "case_packs/"
                    "v0_213_clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_213_clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_pack_validation
                else None,
                "summary": clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_213_clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial": {
                "version": "psm_v0.215",
                "case_pack": (
                    "case_packs/"
                    "v0_215_clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_215_clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_pack_validation
                else None,
                "summary": clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_215_clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
            "clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial": {
                "version": "psm_v0.217",
                "case_pack": (
                    "case_packs/"
                    "v0_217_clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_cases.json"
                ),
                "validation": (
                    "case_packs/"
                    "v0_217_clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_cases_validation.json"
                ),
                "available": clean_external_medical_future_judging_empty_fixture_surveillance_boundary_pack_validation
                is not None,
                "passed": clean_external_medical_future_judging_empty_fixture_surveillance_boundary_pack_validation.get(
                    "passed"
                )
                if clean_external_medical_future_judging_empty_fixture_surveillance_boundary_pack_validation
                else None,
                "summary": clean_external_medical_future_judging_empty_fixture_surveillance_boundary_pack_validation.get(
                    "summary", {}
                )
                if clean_external_medical_future_judging_empty_fixture_surveillance_boundary_pack_validation
                else {},
                "formal_case_file": (
                    "cases/"
                    "v0_217_clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_cases.json"
                ),
                "loaded_by_default_case_loader": True,
                "rule_replacement_allowed": False,
            },
        },
        "primary_artifacts": {
            "current_status": "CURRENT_STATUS.md",
            "readme": "README.md",
            "adapter_contract": "MODEL_ADAPTER_SPEC.md",
            "candidate_taxonomy": f"taxonomy_out/{source_stem}_candidate_taxonomy.json",
            "candidate_taxonomy_report": f"taxonomy_out/PSM_{source_stem_to_tag(source_stem)}_Candidate_Taxonomy_Report.md",
            "candidate_regression_fixtures": f"fixture_out/{source_stem}_candidate_regression_fixtures.json",
            "candidate_regression_fixtures_report": f"fixture_out/PSM_{source_stem_to_tag(source_stem)}_Candidate_Regression_Fixtures_Report.md",
            "taxonomy_delta": f"taxonomy_delta_out/{source_stem}_taxonomy_delta.json",
            "taxonomy_delta_report": f"taxonomy_delta_out/PSM_{source_stem_to_tag(source_stem)}_Taxonomy_Delta_Report.md",
            "evaluator_blindspot_case_pack": "case_packs/v0_19_evaluator_blindspot_cases.json",
            "evaluator_blindspot_case_pack_report": "case_packs/PSM_V0.19_Evaluator_Blindspot_Case_Pack_Report.md",
            "candidate_metrics": f"candidate_holdout_out/{source_stem}_candidate_holdout_metrics.json",
            "candidate_ledger": f"candidate_holdout_out/{source_stem}_candidate_failure_ledger.jsonl",
            "optional_external_full_required_fault_metrics": "candidate_external_out/psm_v0.218_candidate_holdout_metrics.json",
            "optional_external_full_required_fault_report": "candidate_external_out/PSM_V0.218_Candidate_Holdout_Comparison_Report.md",
            "optional_external_metrics": f"candidate_external_out/{OPTIONAL_EXTERNAL_STEM}_candidate_holdout_metrics.json",
            "optional_external_ledger": f"candidate_external_out/{OPTIONAL_EXTERNAL_STEM}_candidate_failure_ledger.jsonl",
            "optional_external_taxonomy": f"taxonomy_external_out/{OPTIONAL_EXTERNAL_STEM}_candidate_taxonomy.json",
            "optional_external_taxonomy_delta": f"taxonomy_external_delta_out/{OPTIONAL_EXTERNAL_STEM}_taxonomy_delta.json",
            "optional_external_regression": f"regression_external_out/{OPTIONAL_EXTERNAL_STEM}_optional_external_regression_check.json",
            "optional_external_risk_fixtures": f"external_risk_out/{OPTIONAL_EXTERNAL_STEM}_optional_external_risk_fixtures.json",
            "optional_external_risk_report": f"external_risk_out/PSM_{source_stem_to_tag(OPTIONAL_EXTERNAL_STEM)}_Optional_External_Risk_Fixtures_Report.md",
            "optional_external_fixture_regression": f"external_fixture_regression_out/{OPTIONAL_EXTERNAL_STEM}_optional_external_fixture_regression.json",
            "optional_external_fixture_regression_report": f"external_fixture_regression_out/PSM_{source_stem_to_tag(OPTIONAL_EXTERNAL_STEM)}_Optional_External_Fixture_Regression_Report.md",
            "optional_external_hardening_check": f"external_hardening_out/{OPTIONAL_EXTERNAL_HARDENING_STEM}_optional_external_hardening_check.json",
            "optional_external_hardening_report": f"external_hardening_out/PSM_{source_stem_to_tag(OPTIONAL_EXTERNAL_HARDENING_STEM)}_Optional_External_Hardening_Check_Report.md",
            "optional_external_residual_regression": optional_residual_regression_artifact
            if Path(optional_residual_regression_artifact).exists()
            else None,
            "optional_external_residual_report": optional_residual_report_artifact
            if Path(optional_residual_report_artifact).exists()
            else None,
            "optional_external_residual_case_pack": optional_residual_case_pack
            if Path(optional_residual_case_pack).exists()
            else None,
            "optional_external_reaudit_metrics": f"candidate_external_reaudit_out/{OPTIONAL_EXTERNAL_REAUDIT_STEM}_candidate_reaudit_metrics.json",
            "optional_external_reaudit_report": f"candidate_external_reaudit_out/PSM_{source_stem_to_tag(OPTIONAL_EXTERNAL_REAUDIT_STEM)}_Candidate_Reaudit_Report.md",
            "optional_external_evidence_trend": f"evidence_trend_out/{EVIDENCE_TREND_STEM}_optional_external_evidence_trend.json",
            "optional_external_evidence_trend_report": f"evidence_trend_out/PSM_{source_stem_to_tag(EVIDENCE_TREND_STEM)}_Optional_External_Evidence_Trend_Report.md",
            "optional_external_release_summary": f"release_out/{RELEASE_SUMMARY_STEM}_optional_external_release_summary.json",
            "optional_external_release_report": f"release_out/PSM_{source_stem_to_tag(RELEASE_SUMMARY_STEM)}_Optional_External_Release_Summary.md",
            "next_expansion_family": f"expansion_out/{RELEASE_SUMMARY_STEM}_next_expansion_family.json",
            "next_expansion_family_report": f"expansion_out/PSM_{source_stem_to_tag(RELEASE_SUMMARY_STEM)}_Next_Expansion_Family.md",
            "meta_boundary_adversarial_case_pack": "case_packs/v0_29_meta_boundary_adversarial_cases.json",
            "meta_boundary_adversarial_validation": "case_packs/v0_29_meta_boundary_adversarial_cases_validation.json",
            "meta_boundary_adversarial_report": "case_packs/PSM_V0.29_V0_29_Meta_Boundary_Adversarial_Cases_Report.md",
            "meta_boundary_adversarial_formal_cases": "cases/v0_30_meta_boundary_adversarial_cases.json",
            "contextual_boundary_adversarial_case_pack": "case_packs/v0_34_contextual_boundary_adversarial_cases.json",
            "contextual_boundary_adversarial_validation": "case_packs/v0_34_contextual_boundary_adversarial_cases_validation.json",
            "contextual_boundary_adversarial_report": "case_packs/PSM_V0.34_V0_34_Contextual_Boundary_Adversarial_Cases_Report.md",
            "contextual_boundary_adversarial_formal_cases": "cases/v0_34_contextual_boundary_adversarial_cases.json",
            "protocol_action_boundary_adversarial_case_pack": "case_packs/v0_37_protocol_action_boundary_adversarial_cases.json",
            "protocol_action_boundary_adversarial_validation": "case_packs/v0_37_protocol_action_boundary_adversarial_cases_validation.json",
            "protocol_action_boundary_adversarial_report": "case_packs/PSM_V0.37_V0_37_Protocol_Action_Boundary_Adversarial_Cases_Report.md",
            "protocol_action_boundary_adversarial_formal_cases": "cases/v0_37_protocol_action_boundary_adversarial_cases.json",
            "temporal_recovery_boundary_adversarial_case_pack": "case_packs/v0_40_temporal_recovery_boundary_adversarial_cases.json",
            "temporal_recovery_boundary_adversarial_validation": "case_packs/v0_40_temporal_recovery_boundary_adversarial_cases_validation.json",
            "temporal_recovery_boundary_adversarial_report": "case_packs/PSM_V0.40_V0_40_Temporal_Recovery_Boundary_Adversarial_Cases_Report.md",
            "temporal_recovery_boundary_adversarial_formal_cases": "cases/v0_40_temporal_recovery_boundary_adversarial_cases.json",
            "auditor_context_residual_adversarial_case_pack": "case_packs/v0_44_auditor_context_residual_adversarial_cases.json",
            "auditor_context_residual_adversarial_validation": "case_packs/v0_44_auditor_context_residual_adversarial_cases_validation.json",
            "auditor_context_residual_adversarial_report": "case_packs/PSM_V0.44_V0_44_Auditor_Context_Residual_Adversarial_Cases_Report.md",
            "auditor_context_residual_adversarial_formal_cases": "cases/v0_44_auditor_context_residual_adversarial_cases.json",
            "optional_release_freshness_adversarial_case_pack": "case_packs/v0_47_optional_release_freshness_adversarial_cases.json",
            "optional_release_freshness_adversarial_validation": "case_packs/v0_47_optional_release_freshness_adversarial_cases_validation.json",
            "optional_release_freshness_adversarial_report": "case_packs/PSM_V0.47_V0_47_Optional_Release_Freshness_Adversarial_Cases_Report.md",
            "optional_release_freshness_adversarial_formal_cases": "cases/v0_47_optional_release_freshness_adversarial_cases.json",
            "optional_raw_overclaim_residual_adversarial_case_pack": "case_packs/v0_49_optional_raw_overclaim_residual_adversarial_cases.json",
            "optional_raw_overclaim_residual_adversarial_validation": "case_packs/v0_49_optional_raw_overclaim_residual_adversarial_cases_validation.json",
            "optional_raw_overclaim_residual_adversarial_report": "case_packs/PSM_V0.49_V0_49_Optional_Raw_Overclaim_Residual_Adversarial_Cases_Report.md",
            "optional_raw_overclaim_residual_adversarial_formal_cases": "cases/v0_49_optional_raw_overclaim_residual_adversarial_cases.json",
            "residual_closure_release_boundary_adversarial_case_pack": "case_packs/v0_52_residual_closure_release_boundary_adversarial_cases.json",
            "residual_closure_release_boundary_adversarial_validation": "case_packs/v0_52_residual_closure_release_boundary_adversarial_cases_validation.json",
            "residual_closure_release_boundary_adversarial_report": "case_packs/PSM_V0.52_V0_52_Residual_Closure_Release_Boundary_Adversarial_Cases_Report.md",
            "residual_closure_release_boundary_adversarial_formal_cases": "cases/v0_52_residual_closure_release_boundary_adversarial_cases.json",
            "external_coverage_state_transition_adversarial_case_pack": "case_packs/v0_55_external_coverage_state_transition_adversarial_cases.json",
            "external_coverage_state_transition_adversarial_validation": "case_packs/v0_55_external_coverage_state_transition_adversarial_cases_validation.json",
            "external_coverage_state_transition_adversarial_report": "case_packs/PSM_V0.55_V0_55_External_Coverage_State_Transition_Adversarial_Cases_Report.md",
            "external_coverage_state_transition_adversarial_formal_cases": "cases/v0_55_external_coverage_state_transition_adversarial_cases.json",
            "residual_raw_success_boundary_adversarial_case_pack": "case_packs/v0_57_residual_raw_success_boundary_adversarial_cases.json",
            "residual_raw_success_boundary_adversarial_validation": "case_packs/v0_57_residual_raw_success_boundary_adversarial_cases_validation.json",
            "residual_raw_success_boundary_adversarial_report": "case_packs/PSM_V0.57_V0_57_Residual_Raw_Success_Boundary_Adversarial_Cases_Report.md",
            "residual_raw_success_boundary_adversarial_formal_cases": "cases/v0_57_residual_raw_success_boundary_adversarial_cases.json",
            "negated_boundary_overclaim_residual_adversarial_case_pack": "case_packs/v0_59_negated_boundary_overclaim_residual_adversarial_cases.json",
            "negated_boundary_overclaim_residual_adversarial_validation": "case_packs/v0_59_negated_boundary_overclaim_residual_adversarial_cases_validation.json",
            "negated_boundary_overclaim_residual_adversarial_report": "case_packs/PSM_V0.59_V0_59_Negated_Boundary_Overclaim_Residual_Adversarial_Cases_Report.md",
            "negated_boundary_overclaim_residual_adversarial_formal_cases": "cases/v0_59_negated_boundary_overclaim_residual_adversarial_cases.json",
            "release_literal_sanitization_boundary_adversarial_case_pack": "case_packs/v0_63_release_literal_sanitization_boundary_adversarial_cases.json",
            "release_literal_sanitization_boundary_adversarial_validation": "case_packs/v0_63_release_literal_sanitization_boundary_adversarial_cases_validation.json",
            "release_literal_sanitization_boundary_adversarial_report": "case_packs/PSM_V0.63_V0_63_Release_Literal_Sanitization_Boundary_Adversarial_Cases_Report.md",
            "release_literal_sanitization_boundary_adversarial_formal_cases": "cases/v0_63_release_literal_sanitization_boundary_adversarial_cases.json",
            "external_evidence_layering_timeout_boundary_adversarial_case_pack": "case_packs/v0_65_external_evidence_layering_timeout_boundary_adversarial_cases.json",
            "external_evidence_layering_timeout_boundary_adversarial_validation": "case_packs/v0_65_external_evidence_layering_timeout_boundary_adversarial_cases_validation.json",
            "external_evidence_layering_timeout_boundary_adversarial_report": "case_packs/PSM_V0.65_V0_65_External_Evidence_Layering_Timeout_Boundary_Adversarial_Cases_Report.md",
            "external_evidence_layering_timeout_boundary_adversarial_formal_cases": "cases/v0_65_external_evidence_layering_timeout_boundary_adversarial_cases.json",
            "negative_scope_overclaim_rescue_adversarial_case_pack": "case_packs/v0_67_negative_scope_overclaim_rescue_adversarial_cases.json",
            "negative_scope_overclaim_rescue_adversarial_validation": "case_packs/v0_67_negative_scope_overclaim_rescue_adversarial_cases_validation.json",
            "negative_scope_overclaim_rescue_adversarial_report": "case_packs/PSM_V0.67_V0_67_Negative_Scope_Overclaim_Rescue_Adversarial_Cases_Report.md",
            "negative_scope_overclaim_rescue_adversarial_formal_cases": "cases/v0_67_negative_scope_overclaim_rescue_adversarial_cases.json",
            "ordinary_external_output_authority_boundary_adversarial_case_pack": "case_packs/v0_69_ordinary_external_output_authority_boundary_adversarial_cases.json",
            "ordinary_external_output_authority_boundary_adversarial_validation": "case_packs/v0_69_ordinary_external_output_authority_boundary_adversarial_cases_validation.json",
            "ordinary_external_output_authority_boundary_adversarial_report": "case_packs/PSM_V0.69_V0_69_Ordinary_External_Output_Authority_Boundary_Adversarial_Cases_Report.md",
            "ordinary_external_output_authority_boundary_adversarial_formal_cases": "cases/v0_69_ordinary_external_output_authority_boundary_adversarial_cases.json",
            "external_clean_permission_rescue_adversarial_case_pack": "case_packs/v0_71_external_clean_permission_rescue_adversarial_cases.json",
            "external_clean_permission_rescue_adversarial_validation": "case_packs/v0_71_external_clean_permission_rescue_adversarial_cases_validation.json",
            "external_clean_permission_rescue_adversarial_report": "case_packs/PSM_V0.71_V0_71_External_Clean_Permission_Rescue_Adversarial_Cases_Report.md",
            "external_clean_permission_rescue_adversarial_formal_cases": "cases/v0_71_external_clean_permission_rescue_adversarial_cases.json",
            "trading_external_clean_overclaim_rescue_adversarial_case_pack": "case_packs/v0_73_trading_external_clean_overclaim_rescue_adversarial_cases.json",
            "trading_external_clean_overclaim_rescue_adversarial_validation": "case_packs/v0_73_trading_external_clean_overclaim_rescue_adversarial_cases_validation.json",
            "trading_external_clean_overclaim_rescue_adversarial_report": "case_packs/PSM_V0.73_V0_73_Trading_External_Clean_Overclaim_Rescue_Adversarial_Cases_Report.md",
            "trading_external_clean_overclaim_rescue_adversarial_formal_cases": "cases/v0_73_trading_external_clean_overclaim_rescue_adversarial_cases.json",
            "trading_polarity_scope_overclaim_rescue_adversarial_case_pack": "case_packs/v0_75_trading_polarity_scope_overclaim_rescue_adversarial_cases.json",
            "trading_polarity_scope_overclaim_rescue_adversarial_validation": "case_packs/v0_75_trading_polarity_scope_overclaim_rescue_adversarial_cases_validation.json",
            "trading_polarity_scope_overclaim_rescue_adversarial_report": "case_packs/PSM_V0.75_V0_75_Trading_Polarity_Scope_Overclaim_Rescue_Adversarial_Cases_Report.md",
            "trading_polarity_scope_overclaim_rescue_adversarial_formal_cases": "cases/v0_75_trading_polarity_scope_overclaim_rescue_adversarial_cases.json",
            "cross_domain_boundary_phrase_polarity_adversarial_case_pack": "case_packs/v0_77_cross_domain_boundary_phrase_polarity_adversarial_cases.json",
            "cross_domain_boundary_phrase_polarity_adversarial_validation": "case_packs/v0_77_cross_domain_boundary_phrase_polarity_adversarial_cases_validation.json",
            "cross_domain_boundary_phrase_polarity_adversarial_report": "case_packs/PSM_V0.77_V0_77_Cross_Domain_Boundary_Phrase_Polarity_Adversarial_Cases_Report.md",
            "cross_domain_boundary_phrase_polarity_adversarial_formal_cases": "cases/v0_77_cross_domain_boundary_phrase_polarity_adversarial_cases.json",
            "cross_domain_authority_scope_boundary_erasure_adversarial_case_pack": "case_packs/v0_79_cross_domain_authority_scope_boundary_erasure_adversarial_cases.json",
            "cross_domain_authority_scope_boundary_erasure_adversarial_validation": "case_packs/v0_79_cross_domain_authority_scope_boundary_erasure_adversarial_cases_validation.json",
            "cross_domain_authority_scope_boundary_erasure_adversarial_report": "case_packs/PSM_V0.79_V0_79_Cross_Domain_Authority_Scope_Boundary_Erasure_Adversarial_Cases_Report.md",
            "cross_domain_authority_scope_boundary_erasure_adversarial_formal_cases": "cases/v0_79_cross_domain_authority_scope_boundary_erasure_adversarial_cases.json",
            "shared_negative_scope_assurance_verb_adversarial_case_pack": "case_packs/v0_81_shared_negative_scope_assurance_verb_adversarial_cases.json",
            "shared_negative_scope_assurance_verb_adversarial_validation": "case_packs/v0_81_shared_negative_scope_assurance_verb_adversarial_cases_validation.json",
            "shared_negative_scope_assurance_verb_adversarial_report": "case_packs/PSM_V0.81_V0_81_Shared_Negative_Scope_Assurance_Verb_Adversarial_Cases_Report.md",
            "shared_negative_scope_assurance_verb_adversarial_formal_cases": "cases/v0_81_shared_negative_scope_assurance_verb_adversarial_cases.json",
            "quoted_forbidden_phrase_controller_review_adversarial_case_pack": "case_packs/v0_83_quoted_forbidden_phrase_controller_review_adversarial_cases.json",
            "quoted_forbidden_phrase_controller_review_adversarial_validation": "case_packs/v0_83_quoted_forbidden_phrase_controller_review_adversarial_cases_validation.json",
            "quoted_forbidden_phrase_controller_review_adversarial_report": "case_packs/PSM_V0.83_V0_83_Quoted_Forbidden_Phrase_Controller_Review_Adversarial_Cases_Report.md",
            "quoted_forbidden_phrase_controller_review_adversarial_formal_cases": "cases/v0_83_quoted_forbidden_phrase_controller_review_adversarial_cases.json",
            "multilingual_forbidden_phrase_scope_adversarial_case_pack": "case_packs/v0_85_multilingual_forbidden_phrase_scope_adversarial_cases.json",
            "multilingual_forbidden_phrase_scope_adversarial_validation": "case_packs/v0_85_multilingual_forbidden_phrase_scope_adversarial_cases_validation.json",
            "multilingual_forbidden_phrase_scope_adversarial_report": "case_packs/PSM_V0.85_V0_85_Multilingual_Forbidden_Phrase_Scope_Adversarial_Cases_Report.md",
            "multilingual_forbidden_phrase_scope_adversarial_formal_cases": "cases/v0_85_multilingual_forbidden_phrase_scope_adversarial_cases.json",
            "external_review_overclaim_residual_adversarial_case_pack": "case_packs/v0_87_external_review_overclaim_residual_adversarial_cases.json",
            "external_review_overclaim_residual_adversarial_validation": "case_packs/v0_87_external_review_overclaim_residual_adversarial_cases_validation.json",
            "external_review_overclaim_residual_adversarial_report": "case_packs/PSM_V0.87_V0_87_External_Review_Overclaim_Residual_Adversarial_Cases_Report.md",
            "external_review_overclaim_residual_adversarial_formal_cases": "cases/v0_87_external_review_overclaim_residual_adversarial_cases.json",
            "external_review_rule_replacement_residual_adversarial_case_pack": "case_packs/v0_89_external_review_rule_replacement_residual_adversarial_cases.json",
            "external_review_rule_replacement_residual_adversarial_validation": "case_packs/v0_89_external_review_rule_replacement_residual_adversarial_cases_validation.json",
            "external_review_rule_replacement_residual_adversarial_report": "case_packs/PSM_V0.89_V0_89_External_Review_Rule_Replacement_Residual_Adversarial_Cases_Report.md",
            "external_review_rule_replacement_residual_adversarial_formal_cases": "cases/v0_89_external_review_rule_replacement_residual_adversarial_cases.json",
            "optional_clean_empty_release_boundary_adversarial_case_pack": "case_packs/v0_91_optional_clean_empty_release_boundary_adversarial_cases.json",
            "optional_clean_empty_release_boundary_adversarial_validation": "case_packs/v0_91_optional_clean_empty_release_boundary_adversarial_cases_validation.json",
            "optional_clean_empty_release_boundary_adversarial_report": "case_packs/PSM_V0.91_V0_91_Optional_Clean_Empty_Release_Boundary_Adversarial_Cases_Report.md",
            "optional_clean_empty_release_boundary_adversarial_formal_cases": "cases/v0_91_optional_clean_empty_release_boundary_adversarial_cases.json",
            "clean_empty_residual_overclaim_boundary_adversarial_case_pack": "case_packs/v0_93_clean_empty_residual_overclaim_boundary_adversarial_cases.json",
            "clean_empty_residual_overclaim_boundary_adversarial_validation": "case_packs/v0_93_clean_empty_residual_overclaim_boundary_adversarial_cases_validation.json",
            "clean_empty_residual_overclaim_boundary_adversarial_report": "case_packs/PSM_V0.93_V0_93_Clean_Empty_Residual_Overclaim_Boundary_Adversarial_Cases_Report.md",
            "clean_empty_residual_overclaim_boundary_adversarial_formal_cases": "cases/v0_93_clean_empty_residual_overclaim_boundary_adversarial_cases.json",
            "no_target_read_closure_authority_residual_adversarial_case_pack": "case_packs/v0_95_no_target_read_closure_authority_residual_adversarial_cases.json",
            "no_target_read_closure_authority_residual_adversarial_validation": "case_packs/v0_95_no_target_read_closure_authority_residual_adversarial_cases_validation.json",
            "no_target_read_closure_authority_residual_adversarial_report": "case_packs/PSM_V0.95_V0_95_No_Target_Read_Closure_Authority_Residual_Adversarial_Cases_Report.md",
            "no_target_read_closure_authority_residual_adversarial_formal_cases": "cases/v0_95_no_target_read_closure_authority_residual_adversarial_cases.json",
            "authority_transfer_deployment_residual_adversarial_case_pack": "case_packs/v0_97_authority_transfer_deployment_residual_adversarial_cases.json",
            "authority_transfer_deployment_residual_adversarial_validation": "case_packs/v0_97_authority_transfer_deployment_residual_adversarial_cases_validation.json",
            "authority_transfer_deployment_residual_adversarial_report": "case_packs/PSM_V0.97_V0_97_Authority_Transfer_Deployment_Residual_Adversarial_Cases_Report.md",
            "authority_transfer_deployment_residual_adversarial_formal_cases": "cases/v0_97_authority_transfer_deployment_residual_adversarial_cases.json",
            "controller_rescue_proof_deployment_residual_adversarial_case_pack": "case_packs/v0_99_controller_rescue_proof_deployment_residual_adversarial_cases.json",
            "controller_rescue_proof_deployment_residual_adversarial_validation": "case_packs/v0_99_controller_rescue_proof_deployment_residual_adversarial_cases_validation.json",
            "controller_rescue_proof_deployment_residual_adversarial_report": "case_packs/PSM_V0.99_V0_99_Controller_Rescue_Proof_Deployment_Residual_Adversarial_Cases_Report.md",
            "controller_rescue_proof_deployment_residual_adversarial_formal_cases": "cases/v0_99_controller_rescue_proof_deployment_residual_adversarial_cases.json",
            "clean_empty_external_evidence_authority_boundary_adversarial_case_pack": "case_packs/v0_101_clean_empty_external_evidence_authority_boundary_adversarial_cases.json",
            "clean_empty_external_evidence_authority_boundary_adversarial_validation": "case_packs/v0_101_clean_empty_external_evidence_authority_boundary_adversarial_cases_validation.json",
            "clean_empty_external_evidence_authority_boundary_adversarial_report": "case_packs/PSM_V0.101_V0_101_Clean_Empty_External_Evidence_Authority_Boundary_Adversarial_Cases_Report.md",
            "clean_empty_external_evidence_authority_boundary_adversarial_formal_cases": "cases/v0_101_clean_empty_external_evidence_authority_boundary_adversarial_cases.json",
            "code_clean_empty_rule_replacement_deployment_residual_adversarial_case_pack": "case_packs/v0_103_code_clean_empty_rule_replacement_deployment_residual_adversarial_cases.json",
            "code_clean_empty_rule_replacement_deployment_residual_adversarial_validation": "case_packs/v0_103_code_clean_empty_rule_replacement_deployment_residual_adversarial_cases_validation.json",
            "code_clean_empty_rule_replacement_deployment_residual_adversarial_report": "case_packs/PSM_V0.103_V0_103_Code_Clean_Empty_Rule_Replacement_Deployment_Residual_Adversarial_Cases_Report.md",
            "code_clean_empty_rule_replacement_deployment_residual_adversarial_formal_cases": "cases/v0_103_code_clean_empty_rule_replacement_deployment_residual_adversarial_cases.json",
            "guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_case_pack": "case_packs/v0_105_guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_cases.json",
            "guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_validation": "case_packs/v0_105_guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_cases_validation.json",
            "guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_report": "case_packs/PSM_V0.105_V0_105_Guarded_Code_Evidence_Rule_Replacement_Overclaim_Residual_Adversarial_Cases_Report.md",
            "guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_formal_cases": "cases/v0_105_guarded_code_evidence_rule_replacement_overclaim_residual_adversarial_cases.json",
            "code_evidence_ci_failure_ledger_overclaim_residual_adversarial_case_pack": "case_packs/v0_107_code_evidence_ci_failure_ledger_overclaim_residual_adversarial_cases.json",
            "code_evidence_ci_failure_ledger_overclaim_residual_adversarial_validation": "case_packs/v0_107_code_evidence_ci_failure_ledger_overclaim_residual_adversarial_cases_validation.json",
            "code_evidence_ci_failure_ledger_overclaim_residual_adversarial_report": "case_packs/PSM_V0.107_V0_107_Code_Evidence_Ci_Failure_Ledger_Overclaim_Residual_Adversarial_Cases_Report.md",
            "code_evidence_ci_failure_ledger_overclaim_residual_adversarial_formal_cases": "cases/v0_107_code_evidence_ci_failure_ledger_overclaim_residual_adversarial_cases.json",
            "ci_completion_guarded_summary_failure_ledger_residual_adversarial_case_pack": "case_packs/v0_109_ci_completion_guarded_summary_failure_ledger_residual_adversarial_cases.json",
            "ci_completion_guarded_summary_failure_ledger_residual_adversarial_validation": "case_packs/v0_109_ci_completion_guarded_summary_failure_ledger_residual_adversarial_cases_validation.json",
            "ci_completion_guarded_summary_failure_ledger_residual_adversarial_report": "case_packs/PSM_V0.109_V0_109_Ci_Completion_Guarded_Summary_Failure_Ledger_Residual_Adversarial_Cases_Report.md",
            "ci_completion_guarded_summary_failure_ledger_residual_adversarial_formal_cases": "cases/v0_109_ci_completion_guarded_summary_failure_ledger_residual_adversarial_cases.json",
            "release_note_noncompletion_state_overclaim_residual_adversarial_case_pack": "case_packs/v0_111_release_note_noncompletion_state_overclaim_residual_adversarial_cases.json",
            "release_note_noncompletion_state_overclaim_residual_adversarial_validation": "case_packs/v0_111_release_note_noncompletion_state_overclaim_residual_adversarial_cases_validation.json",
            "release_note_noncompletion_state_overclaim_residual_adversarial_report": "case_packs/PSM_V0.111_V0_111_Release_Note_Noncompletion_State_Overclaim_Residual_Adversarial_Cases_Report.md",
            "release_note_noncompletion_state_overclaim_residual_adversarial_formal_cases": "cases/v0_111_release_note_noncompletion_state_overclaim_residual_adversarial_cases.json",
            "guarded_controller_rescue_release_completion_overclaim_residual_adversarial_case_pack": "case_packs/v0_113_guarded_controller_rescue_release_completion_overclaim_residual_adversarial_cases.json",
            "guarded_controller_rescue_release_completion_overclaim_residual_adversarial_validation": "case_packs/v0_113_guarded_controller_rescue_release_completion_overclaim_residual_adversarial_cases_validation.json",
            "guarded_controller_rescue_release_completion_overclaim_residual_adversarial_report": "case_packs/PSM_V0.113_V0_113_Guarded_Controller_Rescue_Release_Completion_Overclaim_Residual_Adversarial_Cases_Report.md",
            "guarded_controller_rescue_release_completion_overclaim_residual_adversarial_formal_cases": "cases/v0_113_guarded_controller_rescue_release_completion_overclaim_residual_adversarial_cases.json",
            "psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_case_pack": "case_packs/v0_115_psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_cases.json",
            "psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_validation": "case_packs/v0_115_psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_cases_validation.json",
            "psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_report": "case_packs/PSM_V0.115_V0_115_Psm_Rescue_Engineering_Proof_Ci_Rollback_Overclaim_Residual_Adversarial_Cases_Report.md",
            "psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_formal_cases": "cases/v0_115_psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial_cases.json",
            "psm_rescue_release_completion_review_state_overclaim_residual_adversarial_case_pack": "case_packs/v0_117_psm_rescue_release_completion_review_state_overclaim_residual_adversarial_cases.json",
            "psm_rescue_release_completion_review_state_overclaim_residual_adversarial_validation": "case_packs/v0_117_psm_rescue_release_completion_review_state_overclaim_residual_adversarial_cases_validation.json",
            "psm_rescue_release_completion_review_state_overclaim_residual_adversarial_report": "case_packs/PSM_V0.117_V0_117_Psm_Rescue_Release_Completion_Review_State_Overclaim_Residual_Adversarial_Cases_Report.md",
            "psm_rescue_release_completion_review_state_overclaim_residual_adversarial_formal_cases": "cases/v0_117_psm_rescue_release_completion_review_state_overclaim_residual_adversarial_cases.json",
            "clean_empty_review_state_release_authority_residual_adversarial_case_pack": "case_packs/v0_119_clean_empty_review_state_release_authority_residual_adversarial_cases.json",
            "clean_empty_review_state_release_authority_residual_adversarial_validation": "case_packs/v0_119_clean_empty_review_state_release_authority_residual_adversarial_cases_validation.json",
            "clean_empty_review_state_release_authority_residual_adversarial_report": "case_packs/PSM_V0.119_V0_119_Clean_Empty_Review_State_Release_Authority_Residual_Adversarial_Cases_Report.md",
            "clean_empty_review_state_release_authority_residual_adversarial_formal_cases": "cases/v0_119_clean_empty_review_state_release_authority_residual_adversarial_cases.json",
            "clean_empty_authority_review_legal_overclaim_residual_adversarial_case_pack": "case_packs/v0_121_clean_empty_authority_review_legal_overclaim_residual_adversarial_cases.json",
            "clean_empty_authority_review_legal_overclaim_residual_adversarial_validation": "case_packs/v0_121_clean_empty_authority_review_legal_overclaim_residual_adversarial_cases_validation.json",
            "clean_empty_authority_review_legal_overclaim_residual_adversarial_report": "case_packs/PSM_V0.121_V0_121_Clean_Empty_Authority_Review_Legal_Overclaim_Residual_Adversarial_Cases_Report.md",
            "clean_empty_authority_review_legal_overclaim_residual_adversarial_formal_cases": "cases/v0_121_clean_empty_authority_review_legal_overclaim_residual_adversarial_cases.json",
            "clean_empty_meta_language_boundary_phrase_residual_adversarial_case_pack": "case_packs/v0_123_clean_empty_meta_language_boundary_phrase_residual_adversarial_cases.json",
            "clean_empty_meta_language_boundary_phrase_residual_adversarial_validation": "case_packs/v0_123_clean_empty_meta_language_boundary_phrase_residual_adversarial_cases_validation.json",
            "clean_empty_meta_language_boundary_phrase_residual_adversarial_report": "case_packs/PSM_V0.123_V0_123_Clean_Empty_Meta_Language_Boundary_Phrase_Residual_Adversarial_Cases_Report.md",
            "clean_empty_meta_language_boundary_phrase_residual_adversarial_formal_cases": "cases/v0_123_clean_empty_meta_language_boundary_phrase_residual_adversarial_cases.json",
            "empty_optional_rescue_universal_safety_residual_adversarial_case_pack": "case_packs/v0_125_empty_optional_rescue_universal_safety_residual_adversarial_cases.json",
            "empty_optional_rescue_universal_safety_residual_adversarial_validation": "case_packs/v0_125_empty_optional_rescue_universal_safety_residual_adversarial_cases_validation.json",
            "empty_optional_rescue_universal_safety_residual_adversarial_report": "case_packs/PSM_V0.125_V0_125_Empty_Optional_Rescue_Universal_Safety_Residual_Adversarial_Cases_Report.md",
            "empty_optional_rescue_universal_safety_residual_adversarial_formal_cases": "cases/v0_125_empty_optional_rescue_universal_safety_residual_adversarial_cases.json",
            "clean_empty_ordinary_risk_visibility_residual_adversarial_case_pack": "case_packs/v0_127_clean_empty_ordinary_risk_visibility_residual_adversarial_cases.json",
            "clean_empty_ordinary_risk_visibility_residual_adversarial_validation": "case_packs/v0_127_clean_empty_ordinary_risk_visibility_residual_adversarial_cases_validation.json",
            "clean_empty_ordinary_risk_visibility_residual_adversarial_report": "case_packs/PSM_V0.127_V0_127_Clean_Empty_Ordinary_Risk_Visibility_Residual_Adversarial_Cases_Report.md",
            "clean_empty_ordinary_risk_visibility_residual_adversarial_formal_cases": "cases/v0_127_clean_empty_ordinary_risk_visibility_residual_adversarial_cases.json",
            "clean_empty_ordinary_residue_trend_noncompletion_adversarial_case_pack": "case_packs/v0_129_clean_empty_ordinary_residue_trend_noncompletion_adversarial_cases.json",
            "clean_empty_ordinary_residue_trend_noncompletion_adversarial_validation": "case_packs/v0_129_clean_empty_ordinary_residue_trend_noncompletion_adversarial_cases_validation.json",
            "clean_empty_ordinary_residue_trend_noncompletion_adversarial_report": "case_packs/PSM_V0.129_V0_129_Clean_Empty_Ordinary_Residue_Trend_Noncompletion_Adversarial_Cases_Report.md",
            "clean_empty_ordinary_residue_trend_noncompletion_adversarial_formal_cases": "cases/v0_129_clean_empty_ordinary_residue_trend_noncompletion_adversarial_cases.json",
            "clean_external_candidate_writing_overclaim_rescue_adversarial_case_pack": "case_packs/v0_131_clean_external_candidate_writing_overclaim_rescue_adversarial_cases.json",
            "clean_external_candidate_writing_overclaim_rescue_adversarial_validation": "case_packs/v0_131_clean_external_candidate_writing_overclaim_rescue_adversarial_cases_validation.json",
            "clean_external_candidate_writing_overclaim_rescue_adversarial_report": "case_packs/PSM_V0.131_V0_131_Clean_External_Candidate_Writing_Overclaim_Rescue_Adversarial_Cases_Report.md",
            "clean_external_candidate_writing_overclaim_rescue_adversarial_formal_cases": "cases/v0_131_clean_external_candidate_writing_overclaim_rescue_adversarial_cases.json",
            "negated_universal_safety_clean_candidate_rescue_adversarial_case_pack": "case_packs/v0_133_negated_universal_safety_clean_candidate_rescue_adversarial_cases.json",
            "negated_universal_safety_clean_candidate_rescue_adversarial_validation": "case_packs/v0_133_negated_universal_safety_clean_candidate_rescue_adversarial_cases_validation.json",
            "negated_universal_safety_clean_candidate_rescue_adversarial_report": "case_packs/PSM_V0.133_V0_133_Negated_Universal_Safety_Clean_Candidate_Rescue_Adversarial_Cases_Report.md",
            "negated_universal_safety_clean_candidate_rescue_adversarial_formal_cases": "cases/v0_133_negated_universal_safety_clean_candidate_rescue_adversarial_cases.json",
            "clean_empty_negated_safety_release_boundary_adversarial_case_pack": "case_packs/v0_135_clean_empty_negated_safety_release_boundary_adversarial_cases.json",
            "clean_empty_negated_safety_release_boundary_adversarial_validation": "case_packs/v0_135_clean_empty_negated_safety_release_boundary_adversarial_cases_validation.json",
            "clean_empty_negated_safety_release_boundary_adversarial_report": "case_packs/PSM_V0.135_V0_135_Clean_Empty_Negated_Safety_Release_Boundary_Adversarial_Cases_Report.md",
            "clean_empty_negated_safety_release_boundary_adversarial_formal_cases": "cases/v0_135_clean_empty_negated_safety_release_boundary_adversarial_cases.json",
            "clean_empty_external_refresh_completion_boundary_adversarial_case_pack": "case_packs/v0_137_clean_empty_external_refresh_completion_boundary_adversarial_cases.json",
            "clean_empty_external_refresh_completion_boundary_adversarial_validation": "case_packs/v0_137_clean_empty_external_refresh_completion_boundary_adversarial_cases_validation.json",
            "clean_empty_external_refresh_completion_boundary_adversarial_report": "case_packs/PSM_V0.137_V0_137_Clean_Empty_External_Refresh_Completion_Boundary_Adversarial_Cases_Report.md",
            "clean_empty_external_refresh_completion_boundary_adversarial_formal_cases": "cases/v0_137_clean_empty_external_refresh_completion_boundary_adversarial_cases.json",
            "code_go_live_controller_rescue_external_refresh_boundary_adversarial_case_pack": "case_packs/v0_139_code_go_live_controller_rescue_external_refresh_boundary_adversarial_cases.json",
            "code_go_live_controller_rescue_external_refresh_boundary_adversarial_validation": "case_packs/v0_139_code_go_live_controller_rescue_external_refresh_boundary_adversarial_cases_validation.json",
            "code_go_live_controller_rescue_external_refresh_boundary_adversarial_report": "case_packs/PSM_V0.139_V0_139_Code_Go_Live_Controller_Rescue_External_Refresh_Boundary_Adversarial_Cases_Report.md",
            "code_go_live_controller_rescue_external_refresh_boundary_adversarial_formal_cases": "cases/v0_139_code_go_live_controller_rescue_external_refresh_boundary_adversarial_cases.json",
            "code_go_live_guarantee_variant_rescue_boundary_adversarial_case_pack": "case_packs/v0_141_code_go_live_guarantee_variant_rescue_boundary_adversarial_cases.json",
            "code_go_live_guarantee_variant_rescue_boundary_adversarial_validation": "case_packs/v0_141_code_go_live_guarantee_variant_rescue_boundary_adversarial_cases_validation.json",
            "code_go_live_guarantee_variant_rescue_boundary_adversarial_report": "case_packs/PSM_V0.141_V0_141_Code_Go_Live_Guarantee_Variant_Rescue_Boundary_Adversarial_Cases_Report.md",
            "code_go_live_guarantee_variant_rescue_boundary_adversarial_formal_cases": "cases/v0_141_code_go_live_guarantee_variant_rescue_boundary_adversarial_cases.json",
            "clean_empty_go_live_variant_release_boundary_adversarial_case_pack": "case_packs/v0_143_clean_empty_go_live_variant_release_boundary_adversarial_cases.json",
            "clean_empty_go_live_variant_release_boundary_adversarial_validation": "case_packs/v0_143_clean_empty_go_live_variant_release_boundary_adversarial_cases_validation.json",
            "clean_empty_go_live_variant_release_boundary_adversarial_report": "case_packs/PSM_V0.143_V0_143_Clean_Empty_Go_Live_Variant_Release_Boundary_Adversarial_Cases_Report.md",
            "clean_empty_go_live_variant_release_boundary_adversarial_formal_cases": "cases/v0_143_clean_empty_go_live_variant_release_boundary_adversarial_cases.json",
            "clean_empty_controller_rescue_release_completion_boundary_adversarial_case_pack": "case_packs/v0_145_clean_empty_controller_rescue_release_completion_boundary_adversarial_cases.json",
            "clean_empty_controller_rescue_release_completion_boundary_adversarial_validation": "case_packs/v0_145_clean_empty_controller_rescue_release_completion_boundary_adversarial_cases_validation.json",
            "clean_empty_controller_rescue_release_completion_boundary_adversarial_report": "case_packs/PSM_V0.145_V0_145_Clean_Empty_Controller_Rescue_Release_Completion_Boundary_Adversarial_Cases_Report.md",
            "clean_empty_controller_rescue_release_completion_boundary_adversarial_formal_cases": "cases/v0_145_clean_empty_controller_rescue_release_completion_boundary_adversarial_cases.json",
            "code_controller_rescue_rollback_production_ready_residual_adversarial_case_pack": "case_packs/v0_147_code_controller_rescue_rollback_production_ready_residual_adversarial_cases.json",
            "code_controller_rescue_rollback_production_ready_residual_adversarial_validation": "case_packs/v0_147_code_controller_rescue_rollback_production_ready_residual_adversarial_cases_validation.json",
            "code_controller_rescue_rollback_production_ready_residual_adversarial_report": "case_packs/PSM_V0.147_V0_147_Code_Controller_Rescue_Rollback_Production_Ready_Residual_Adversarial_Cases_Report.md",
            "code_controller_rescue_rollback_production_ready_residual_adversarial_formal_cases": "cases/v0_147_code_controller_rescue_rollback_production_ready_residual_adversarial_cases.json",
            "code_monitoring_omission_controller_rescue_residual_adversarial_case_pack": "case_packs/v0_149_code_monitoring_omission_controller_rescue_residual_adversarial_cases.json",
            "code_monitoring_omission_controller_rescue_residual_adversarial_validation": "case_packs/v0_149_code_monitoring_omission_controller_rescue_residual_adversarial_cases_validation.json",
            "code_monitoring_omission_controller_rescue_residual_adversarial_report": "case_packs/PSM_V0.149_V0_149_Code_Monitoring_Omission_Controller_Rescue_Residual_Adversarial_Cases_Report.md",
            "code_monitoring_omission_controller_rescue_residual_adversarial_formal_cases": "cases/v0_149_code_monitoring_omission_controller_rescue_residual_adversarial_cases.json",
            "clean_empty_monitoring_observability_release_boundary_adversarial_case_pack": "case_packs/v0_151_clean_empty_monitoring_observability_release_boundary_adversarial_cases.json",
            "clean_empty_monitoring_observability_release_boundary_adversarial_validation": "case_packs/v0_151_clean_empty_monitoring_observability_release_boundary_adversarial_cases_validation.json",
            "clean_empty_monitoring_observability_release_boundary_adversarial_report": "case_packs/PSM_V0.151_V0_151_Clean_Empty_Monitoring_Observability_Release_Boundary_Adversarial_Cases_Report.md",
            "clean_empty_monitoring_observability_release_boundary_adversarial_formal_cases": "cases/v0_151_clean_empty_monitoring_observability_release_boundary_adversarial_cases.json",
            "clean_empty_alert_suppression_controller_rescue_residual_adversarial_case_pack": "case_packs/v0_153_clean_empty_alert_suppression_controller_rescue_residual_adversarial_cases.json",
            "clean_empty_alert_suppression_controller_rescue_residual_adversarial_validation": "case_packs/v0_153_clean_empty_alert_suppression_controller_rescue_residual_adversarial_cases_validation.json",
            "clean_empty_alert_suppression_controller_rescue_residual_adversarial_report": "case_packs/PSM_V0.153_V0_153_Clean_Empty_Alert_Suppression_Controller_Rescue_Residual_Adversarial_Cases_Report.md",
            "clean_empty_alert_suppression_controller_rescue_residual_adversarial_formal_cases": "cases/v0_153_clean_empty_alert_suppression_controller_rescue_residual_adversarial_cases.json",
            "medical_alert_rescue_patient_safety_residual_adversarial_case_pack": "case_packs/v0_155_medical_alert_rescue_patient_safety_residual_adversarial_cases.json",
            "medical_alert_rescue_patient_safety_residual_adversarial_validation": "case_packs/v0_155_medical_alert_rescue_patient_safety_residual_adversarial_cases_validation.json",
            "medical_alert_rescue_patient_safety_residual_adversarial_report": "case_packs/PSM_V0.155_V0_155_Medical_Alert_Rescue_Patient_Safety_Residual_Adversarial_Cases_Report.md",
            "medical_alert_rescue_patient_safety_residual_adversarial_formal_cases": "cases/v0_155_medical_alert_rescue_patient_safety_residual_adversarial_cases.json",
            "clean_empty_medical_alert_rescue_release_boundary_adversarial_case_pack": "case_packs/v0_157_clean_empty_medical_alert_rescue_release_boundary_adversarial_cases.json",
            "clean_empty_medical_alert_rescue_release_boundary_adversarial_validation": "case_packs/v0_157_clean_empty_medical_alert_rescue_release_boundary_adversarial_cases_validation.json",
            "clean_empty_medical_alert_rescue_release_boundary_adversarial_report": "case_packs/PSM_V0.157_V0_157_Clean_Empty_Medical_Alert_Rescue_Release_Boundary_Adversarial_Cases_Report.md",
            "clean_empty_medical_alert_rescue_release_boundary_adversarial_formal_cases": "cases/v0_157_clean_empty_medical_alert_rescue_release_boundary_adversarial_cases.json",
            "clean_external_medical_release_authority_boundary_adversarial_case_pack": "case_packs/v0_159_clean_external_medical_release_authority_boundary_adversarial_cases.json",
            "clean_external_medical_release_authority_boundary_adversarial_validation": "case_packs/v0_159_clean_external_medical_release_authority_boundary_adversarial_cases_validation.json",
            "clean_external_medical_release_authority_boundary_adversarial_report": "case_packs/PSM_V0.159_V0_159_Clean_External_Medical_Release_Authority_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_release_authority_boundary_adversarial_formal_cases": "cases/v0_159_clean_external_medical_release_authority_boundary_adversarial_cases.json",
            "clean_external_medical_ordinary_risk_visibility_boundary_adversarial_case_pack": "case_packs/v0_161_clean_external_medical_ordinary_risk_visibility_boundary_adversarial_cases.json",
            "clean_external_medical_ordinary_risk_visibility_boundary_adversarial_validation": "case_packs/v0_161_clean_external_medical_ordinary_risk_visibility_boundary_adversarial_cases_validation.json",
            "clean_external_medical_ordinary_risk_visibility_boundary_adversarial_report": "case_packs/PSM_V0.161_V0_161_Clean_External_Medical_Ordinary_Risk_Visibility_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_ordinary_risk_visibility_boundary_adversarial_formal_cases": "cases/v0_161_clean_external_medical_ordinary_risk_visibility_boundary_adversarial_cases.json",
            "clean_external_medical_meta_language_boundary_phrase_adversarial_case_pack": "case_packs/v0_163_clean_external_medical_meta_language_boundary_phrase_adversarial_cases.json",
            "clean_external_medical_meta_language_boundary_phrase_adversarial_validation": "case_packs/v0_163_clean_external_medical_meta_language_boundary_phrase_adversarial_cases_validation.json",
            "clean_external_medical_meta_language_boundary_phrase_adversarial_report": "case_packs/PSM_V0.163_V0_163_Clean_External_Medical_Meta_Language_Boundary_Phrase_Adversarial_Cases_Report.md",
            "clean_external_medical_meta_language_boundary_phrase_adversarial_formal_cases": "cases/v0_163_clean_external_medical_meta_language_boundary_phrase_adversarial_cases.json",
            "clean_external_medical_future_refresh_meta_boundary_adversarial_case_pack": "case_packs/v0_165_clean_external_medical_future_refresh_meta_boundary_adversarial_cases.json",
            "clean_external_medical_future_refresh_meta_boundary_adversarial_validation": "case_packs/v0_165_clean_external_medical_future_refresh_meta_boundary_adversarial_cases_validation.json",
            "clean_external_medical_future_refresh_meta_boundary_adversarial_report": "case_packs/PSM_V0.165_V0_165_Clean_External_Medical_Future_Refresh_Meta_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_future_refresh_meta_boundary_adversarial_formal_cases": "cases/v0_165_clean_external_medical_future_refresh_meta_boundary_adversarial_cases.json",
            "clean_external_medical_controller_changed_review_boundary_adversarial_case_pack": "case_packs/v0_167_clean_external_medical_controller_changed_review_boundary_adversarial_cases.json",
            "clean_external_medical_controller_changed_review_boundary_adversarial_validation": "case_packs/v0_167_clean_external_medical_controller_changed_review_boundary_adversarial_cases_validation.json",
            "clean_external_medical_controller_changed_review_boundary_adversarial_report": "case_packs/PSM_V0.167_V0_167_Clean_External_Medical_Controller_Changed_Review_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_controller_changed_review_boundary_adversarial_formal_cases": "cases/v0_167_clean_external_medical_controller_changed_review_boundary_adversarial_cases.json",
            "clean_external_medical_auxiliary_evidence_release_boundary_adversarial_case_pack": "case_packs/v0_169_clean_external_medical_auxiliary_evidence_release_boundary_adversarial_cases.json",
            "clean_external_medical_auxiliary_evidence_release_boundary_adversarial_validation": "case_packs/v0_169_clean_external_medical_auxiliary_evidence_release_boundary_adversarial_cases_validation.json",
            "clean_external_medical_auxiliary_evidence_release_boundary_adversarial_report": "case_packs/PSM_V0.169_V0_169_Clean_External_Medical_Auxiliary_Evidence_Release_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_auxiliary_evidence_release_boundary_adversarial_formal_cases": "cases/v0_169_clean_external_medical_auxiliary_evidence_release_boundary_adversarial_cases.json",
            "clean_external_medical_release_summary_authority_transfer_boundary_adversarial_case_pack": "case_packs/v0_171_clean_external_medical_release_summary_authority_transfer_boundary_adversarial_cases.json",
            "clean_external_medical_release_summary_authority_transfer_boundary_adversarial_validation": "case_packs/v0_171_clean_external_medical_release_summary_authority_transfer_boundary_adversarial_cases_validation.json",
            "clean_external_medical_release_summary_authority_transfer_boundary_adversarial_report": "case_packs/PSM_V0.171_V0_171_Clean_External_Medical_Release_Summary_Authority_Transfer_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_release_summary_authority_transfer_boundary_adversarial_formal_cases": "cases/v0_171_clean_external_medical_release_summary_authority_transfer_boundary_adversarial_cases.json",
            "clean_external_medical_owner_signoff_release_boundary_adversarial_case_pack": "case_packs/v0_173_clean_external_medical_owner_signoff_release_boundary_adversarial_cases.json",
            "clean_external_medical_owner_signoff_release_boundary_adversarial_validation": "case_packs/v0_173_clean_external_medical_owner_signoff_release_boundary_adversarial_cases_validation.json",
            "clean_external_medical_owner_signoff_release_boundary_adversarial_report": "case_packs/PSM_V0.173_V0_173_Clean_External_Medical_Owner_Signoff_Release_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_owner_signoff_release_boundary_adversarial_formal_cases": "cases/v0_173_clean_external_medical_owner_signoff_release_boundary_adversarial_cases.json",
            "clean_external_medical_public_safety_deployment_boundary_adversarial_case_pack": "case_packs/v0_175_clean_external_medical_public_safety_deployment_boundary_adversarial_cases.json",
            "clean_external_medical_public_safety_deployment_boundary_adversarial_validation": "case_packs/v0_175_clean_external_medical_public_safety_deployment_boundary_adversarial_cases_validation.json",
            "clean_external_medical_public_safety_deployment_boundary_adversarial_report": "case_packs/PSM_V0.175_V0_175_Clean_External_Medical_Public_Safety_Deployment_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_public_safety_deployment_boundary_adversarial_formal_cases": "cases/v0_175_clean_external_medical_public_safety_deployment_boundary_adversarial_cases.json",
            "clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_case_pack": "case_packs/v0_177_clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_cases.json",
            "clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_validation": "case_packs/v0_177_clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_cases_validation.json",
            "clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_report": "case_packs/PSM_V0.177_V0_177_Clean_External_Medical_Deployment_Summary_Future_Refresh_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_formal_cases": "cases/v0_177_clean_external_medical_deployment_summary_future_refresh_boundary_adversarial_cases.json",
            "clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_case_pack": "case_packs/v0_179_clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_cases.json",
            "clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_validation": "case_packs/v0_179_clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_cases_validation.json",
            "clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_report": "case_packs/PSM_V0.179_V0_179_Clean_External_Medical_Post_Release_Monitoring_Incident_Free_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_formal_cases": "cases/v0_179_clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial_cases.json",
            "clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_case_pack": "case_packs/v0_181_clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_cases.json",
            "clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_validation": "case_packs/v0_181_clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_cases_validation.json",
            "clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_report": "case_packs/PSM_V0.181_V0_181_Clean_External_Medical_Patient_Facing_Assurance_Regulatory_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_formal_cases": "cases/v0_181_clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial_cases.json",
            "clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_case_pack": "case_packs/v0_183_clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_cases.json",
            "clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_validation": "case_packs/v0_183_clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_cases_validation.json",
            "clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_report": "case_packs/PSM_V0.183_V0_183_Clean_External_Medical_Liability_Release_Overclaim_Rescue_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_formal_cases": "cases/v0_183_clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial_cases.json",
            "clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_case_pack": "case_packs/v0_185_clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_cases.json",
            "clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_validation": "case_packs/v0_185_clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_cases_validation.json",
            "clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_report": "case_packs/PSM_V0.185_V0_185_Clean_External_Medical_Liability_Empty_Fixture_Compliance_Closure_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_formal_cases": "cases/v0_185_clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial_cases.json",
            "clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_case_pack": "case_packs/v0_187_clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_cases.json",
            "clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_validation": "case_packs/v0_187_clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_cases_validation.json",
            "clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_report": "case_packs/PSM_V0.187_V0_187_Clean_External_Medical_Regulatory_Acceptance_Overclaim_Rescue_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_formal_cases": "cases/v0_187_clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial_cases.json",
            "clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_case_pack": "case_packs/v0_189_clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_cases.json",
            "clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_validation": "case_packs/v0_189_clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_cases_validation.json",
            "clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_report": "case_packs/PSM_V0.189_V0_189_Clean_External_Medical_Regulatory_Acceptance_Empty_Fixture_Authorization_Closure_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_formal_cases": "cases/v0_189_clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial_cases.json",
            "clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_case_pack": "case_packs/v0_191_clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_cases.json",
            "clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_validation": "case_packs/v0_191_clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_cases_validation.json",
            "clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_report": "case_packs/PSM_V0.191_V0_191_Clean_External_Medical_Authorization_Closure_Empty_Fixture_Deployment_Permission_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_formal_cases": "cases/v0_191_clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial_cases.json",
            "clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_case_pack": "case_packs/v0_193_clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_cases.json",
            "clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_validation": "case_packs/v0_193_clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_cases_validation.json",
            "clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_report": "case_packs/PSM_V0.193_V0_193_Clean_External_Medical_Deployment_Permission_Empty_Fixture_Operational_Rollout_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_formal_cases": "cases/v0_193_clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial_cases.json",
            "clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_case_pack": "case_packs/v0_195_clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_cases.json",
            "clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_validation": "case_packs/v0_195_clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_cases_validation.json",
            "clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_report": "case_packs/PSM_V0.195_V0_195_Clean_External_Medical_Operational_Rollout_Empty_Fixture_Postmarket_Monitoring_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_formal_cases": "cases/v0_195_clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial_cases.json",
            "clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_case_pack": "case_packs/v0_197_clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_cases.json",
            "clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_validation": "case_packs/v0_197_clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_cases_validation.json",
            "clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_report": "case_packs/PSM_V0.197_V0_197_Clean_External_Medical_Postmarket_Monitoring_Empty_Fixture_Surveillance_Closure_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_formal_cases": "cases/v0_197_clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial_cases.json",
            "clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_case_pack": "case_packs/v0_199_clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_cases.json",
            "clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_validation": "case_packs/v0_199_clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_cases_validation.json",
            "clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_report": "case_packs/PSM_V0.199_V0_199_Clean_External_Medical_Surveillance_Closure_Empty_Fixture_Recall_Free_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_formal_cases": "cases/v0_199_clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial_cases.json",
            "clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_case_pack": "case_packs/v0_201_clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_cases.json",
            "clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_validation": "case_packs/v0_201_clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_cases_validation.json",
            "clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_report": "case_packs/PSM_V0.201_V0_201_Clean_External_Medical_Recall_Free_Empty_Fixture_Field_Action_Closure_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_formal_cases": "cases/v0_201_clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial_cases.json",
            "clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_case_pack": "case_packs/v0_203_clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_cases.json",
            "clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_validation": "case_packs/v0_203_clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_cases_validation.json",
            "clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_report": "case_packs/PSM_V0.203_V0_203_Clean_External_Medical_Field_Action_Closure_Empty_Fixture_Corrective_Action_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_formal_cases": "cases/v0_203_clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial_cases.json",
            "clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_case_pack": "case_packs/v0_205_clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_cases.json",
            "clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_validation": "case_packs/v0_205_clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_cases_validation.json",
            "clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_report": "case_packs/PSM_V0.205_V0_205_Clean_External_Medical_Corrective_Action_Empty_Fixture_Remediation_Closure_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_formal_cases": "cases/v0_205_clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial_cases.json",
            "clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_case_pack": "case_packs/v0_207_clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_cases.json",
            "clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_validation": "case_packs/v0_207_clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_cases_validation.json",
            "clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_report": "case_packs/PSM_V0.207_V0_207_Clean_External_Medical_Remediation_Closure_Controller_Rescue_Release_Authority_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_formal_cases": "cases/v0_207_clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial_cases.json",
            "clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_case_pack": "case_packs/v0_209_clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_cases.json",
            "clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_validation": "case_packs/v0_209_clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_cases_validation.json",
            "clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_report": "case_packs/PSM_V0.209_V0_209_Clean_External_Medical_Release_Authority_Empty_Fixture_Post_Rescue_Monitoring_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_formal_cases": "cases/v0_209_clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial_cases.json",
            "clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_case_pack": "case_packs/v0_211_clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_cases.json",
            "clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_validation": "case_packs/v0_211_clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_cases_validation.json",
            "clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_report": "case_packs/PSM_V0.211_V0_211_Clean_External_Medical_Post_Rescue_Monitoring_Empty_Fixture_External_Refresh_Authority_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_formal_cases": "cases/v0_211_clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial_cases.json",
            "clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_case_pack": "case_packs/v0_213_clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_cases.json",
            "clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_validation": "case_packs/v0_213_clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_cases_validation.json",
            "clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_report": "case_packs/PSM_V0.213_V0_213_Clean_External_Medical_External_Refresh_Controller_Rescue_Authority_Closure_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_formal_cases": "cases/v0_213_clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial_cases.json",
            "clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_case_pack": "case_packs/v0_215_clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_cases.json",
            "clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_validation": "case_packs/v0_215_clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_cases_validation.json",
            "clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_report": "case_packs/PSM_V0.215_V0_215_Clean_External_Medical_Authority_Closure_Empty_Fixture_Future_Judging_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_formal_cases": "cases/v0_215_clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial_cases.json",
            "clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_case_pack": "case_packs/v0_217_clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_cases.json",
            "clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_validation": "case_packs/v0_217_clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_cases_validation.json",
            "clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_report": "case_packs/PSM_V0.217_V0_217_Clean_External_Medical_Future_Judging_Empty_Fixture_Surveillance_Boundary_Adversarial_Cases_Report.md",
            "clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_formal_cases": "cases/v0_217_clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial_cases.json",
        },
        "next_stage": {
            "version": "PSM_V0.219",
            "objective": (
                "build and promote the v219_ clean-external medical surveillance empty-fixture "
                "postmarket boundary family so surveillance language, future-judging empty fixtures, "
                "external-refresh summaries, stable taxonomy deltas, and gated-zero summaries cannot "
                "become postmarket clearance, recall-free status, release authority, safety assurance, "
                "operational rollout, external-judge removal, or permission to stop future judging"
            ),
            "blocked": False,
            "requires_user_input": False,
        },
    }


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return read_json(path)


def build_optional_external_status(
    metrics: dict | None,
    regression: dict | None,
    risk: dict | None,
    fixture_regression: dict | None,
    hardening: dict | None,
    residual: dict | None,
    reaudit: dict | None,
    evidence_trend: dict | None,
) -> dict:
    if not metrics:
        return {"available": False}
    optional_adapter_metrics = [
        item for item in metrics.get("adapter_metrics", [])
        if item.get("gate_scope") == "optional_external"
    ]
    optional_adapter_metric = optional_adapter_metrics[0] if optional_adapter_metrics else {}
    return {
        "available": True,
        "version": metrics.get("version"),
        "case_prefixes": metrics.get("case_prefixes", []),
        "holdout_cases": metrics.get("holdout_cases"),
        "external_candidate_text_clean": metrics.get("external_candidate_text_clean"),
        "optional_adapter_failures": metrics.get("optional_adapter_failures"),
        "optional_ordinary_unsafe_or_risky": optional_adapter_metric.get("ordinary_unsafe_or_risky"),
        "optional_raw_psm_unsafe_or_risky": optional_adapter_metric.get("raw_psm_unsafe_or_risky"),
        "optional_gated_psm_unsafe_or_risky": metrics.get("optional_gated_psm_unsafe_or_risky"),
        "optional_controller_rescue_count": optional_adapter_metric.get("controller_rescue_count"),
        "total_controller_rescue_count": metrics.get("controller_rescue_count"),
        "fault_injection_events": metrics.get("fault_injection_events"),
        "fault_gated_psm_unsafe_or_risky": metrics.get("fault_gated_psm_unsafe_or_risky"),
        "optional_adapters": metrics.get("optional_external_adapters", []),
        "optional_adapter_metrics": optional_adapter_metrics,
        "taxonomy_delta_changed_groups": read_optional_json(Path(f"taxonomy_external_delta_out/{OPTIONAL_EXTERNAL_STEM}_taxonomy_delta.json"))
        .get("summary", {})
        .get("changed_groups")
        if Path(f"taxonomy_external_delta_out/{OPTIONAL_EXTERNAL_STEM}_taxonomy_delta.json").exists()
        else None,
        "taxonomy_delta_unexpected_regression": read_optional_json(Path(f"taxonomy_external_delta_out/{OPTIONAL_EXTERNAL_STEM}_taxonomy_delta.json"))
        .get("summary", {})
        .get("unexpected_regression")
        if Path(f"taxonomy_external_delta_out/{OPTIONAL_EXTERNAL_STEM}_taxonomy_delta.json").exists()
        else None,
        "regression_passed": regression.get("passed") if regression else None,
        "risk_analysis_available": risk is not None,
        "risk_analysis_summary": risk.get("summary", {}) if risk else {},
        "risk_analysis_invariants_passed": risk.get("invariants", {}).get("passed") if risk else None,
        "fixture_regression_available": fixture_regression is not None,
        "fixture_regression_passed": fixture_regression.get("passed") if fixture_regression else None,
        "fixture_regression_summary": fixture_regression.get("summary", {}) if fixture_regression else {},
        "hardening_check_available": hardening is not None,
        "hardening_check_passed": hardening.get("passed") if hardening else None,
        "hardening_summary": hardening.get("summary", {}) if hardening else {},
        "residual_regression_available": residual is not None,
        "residual_regression_passed": residual.get("passed") if residual else None,
        "residual_regression_summary": residual.get("summary", {}) if residual else {},
        "reaudit_available": reaudit is not None,
        "reaudit_version": reaudit.get("version") if reaudit else None,
        "reaudit_external_candidate_text_clean": reaudit.get("external_candidate_text_clean") if reaudit else None,
        "reaudit_optional_adapter_metrics": [
            item for item in reaudit.get("adapter_metrics", [])
            if item.get("gate_scope") == "optional_external"
        ] if reaudit else [],
        "evidence_trend_available": evidence_trend is not None,
        "evidence_trend_passed": evidence_trend.get("passed") if evidence_trend else None,
        "evidence_trend_summary": evidence_trend.get("summary", {}) if evidence_trend else {},
    }


def source_stem_to_tag(source_stem: str) -> str:
    return source_stem.replace("psm_v", "V").replace(".", ".")


def read_eval_metrics(path: Path) -> dict:
    metrics = {"report": str(path)}
    if not path.exists():
        return metrics
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Cases:"):
            metrics["cases"] = int(line.split(":", 1)[1].strip())
        elif line.startswith("- Passed:"):
            metrics["passed"] = int(line.split(":", 1)[1].strip())
        elif line.startswith("- Failed:"):
            metrics["failed"] = int(line.split(":", 1)[1].strip())
        elif line.startswith("- Average gate score:"):
            metrics["average_gate_score"] = float(line.split(":", 1)[1].strip())
    return metrics


def build_report(status: dict, json_path: Path) -> str:
    core = status["core_metrics"]
    candidate = status["candidate_output"]
    return "\n".join(
        [
            f"# PSM {source_stem_to_tag(status['current_version'])} Project Status",
            "",
            "## Summary",
            "",
            f"- Current version: `{status['current_version']}`",
            f"- Source evidence version: `{status['source_evidence_version']}`",
            f"- Status JSON: `{json_path}`",
            f"- Eval: {core['eval'].get('passed')}/{core['eval'].get('cases')} passed",
            f"- State records: {core['state_records']}",
            f"- Admission gate passed: {core['admission_gate_passed']}",
            f"- Shadow ledger events: {core['shadow_ledger_events']}",
            f"- Candidate-assisted override events: {core['candidate_assisted_override_events']}",
            f"- Holdout no-retrain ledger events: {core['holdout_no_retrain_ledger_events']}",
            f"- Required candidate text clean: {candidate['candidate_text_clean']}",
            f"- Required-gate external candidate text clean field: {candidate['external_candidate_text_clean'] if candidate['external_candidate_text_clean'] is not None else 'not_applicable'}",
            f"- Fault injection events: {candidate['fault_injection_events']}",
            f"- Controller rescue count: {candidate['controller_rescue_count']}",
            f"- Rule replacement allowed: {status['boundaries']['rule_replacement_allowed']}",
            f"- Optional external evidence available: {status['optional_external_evidence']['available']}",
            f"- Optional external clean: {status['optional_external_evidence'].get('external_candidate_text_clean')}",
            f"- Optional external risk analysis passed: {status['optional_external_evidence'].get('risk_analysis_invariants_passed')}",
            f"- Optional external fixture regression passed: {status['optional_external_evidence'].get('fixture_regression_passed')}",
            f"- Optional external hardening check passed: {status['optional_external_evidence'].get('hardening_check_passed')}",
            f"- Optional residual regression passed: {status['optional_external_evidence'].get('residual_regression_passed')}",
            f"- Optional re-audit clean: {status['optional_external_evidence'].get('reaudit_external_candidate_text_clean')}",
            f"- Optional evidence trend passed: {status['optional_external_evidence'].get('evidence_trend_passed')}",
            f"- Optional release summary passed: {status['release_summary'].get('passed')}",
            f"- Optional release summary fresh for optional version: {status['release_summary'].get('fresh_for_optional_external_version')}",
            f"- Release decision: {status['release_summary'].get('release_decision')}",
            f"- Next expansion family: {status['next_expansion_family'].get('selected_family', {}).get('family_id')}",
            f"- Meta-boundary expansion pack passed: {status['expansion_packs']['meta_boundary_adversarial'].get('passed')}",
            f"- Contextual-boundary expansion pack passed: {status['expansion_packs']['contextual_boundary_adversarial'].get('passed')}",
            f"- Protocol-action expansion pack passed: {status['expansion_packs']['protocol_action_boundary_adversarial'].get('passed')}",
            f"- Temporal-recovery expansion pack passed: {status['expansion_packs']['temporal_recovery_boundary_adversarial'].get('passed')}",
            f"- Auditor-context residual expansion pack passed: {status['expansion_packs']['auditor_context_residual_adversarial'].get('passed')}",
            f"- Optional-release freshness expansion pack passed: {status['expansion_packs']['optional_release_freshness_adversarial'].get('passed')}",
            f"- Optional raw-overclaim residual expansion pack passed: {status['expansion_packs']['optional_raw_overclaim_residual_adversarial'].get('passed')}",
            f"- Residual-closure release-boundary expansion pack passed: {status['expansion_packs']['residual_closure_release_boundary_adversarial'].get('passed')}",
            f"- External-coverage state-transition expansion pack passed: {status['expansion_packs']['external_coverage_state_transition_adversarial'].get('passed')}",
            f"- Residual raw-success boundary expansion pack passed: {status['expansion_packs']['residual_raw_success_boundary_adversarial'].get('passed')}",
            f"- Negated-boundary overclaim residual expansion pack passed: {status['expansion_packs']['negated_boundary_overclaim_residual_adversarial'].get('passed')}",
            f"- Release-literal sanitization boundary expansion pack passed: {status['expansion_packs']['release_literal_sanitization_boundary_adversarial'].get('passed')}",
            f"- External-evidence layering timeout-boundary expansion pack passed: {status['expansion_packs']['external_evidence_layering_timeout_boundary_adversarial'].get('passed')}",
            f"- Negative-scope overclaim rescue expansion pack passed: {status['expansion_packs']['negative_scope_overclaim_rescue_adversarial'].get('passed')}",
            f"- Ordinary external-output authority boundary expansion pack passed: {status['expansion_packs']['ordinary_external_output_authority_boundary_adversarial'].get('passed')}",
            f"- External-clean permission rescue expansion pack passed: {status['expansion_packs']['external_clean_permission_rescue_adversarial'].get('passed')}",
            f"- Trading external-clean overclaim rescue expansion pack passed: {status['expansion_packs']['trading_external_clean_overclaim_rescue_adversarial'].get('passed')}",
            f"- Trading polarity-scope overclaim rescue expansion pack passed: {status['expansion_packs']['trading_polarity_scope_overclaim_rescue_adversarial'].get('passed')}",
            f"- Cross-domain boundary-phrase polarity expansion pack passed: {status['expansion_packs']['cross_domain_boundary_phrase_polarity_adversarial'].get('passed')}",
            f"- Shared negative-scope assurance-verb expansion pack passed: {status['expansion_packs']['shared_negative_scope_assurance_verb_adversarial'].get('passed')}",
            f"- Quoted forbidden-phrase controller-review expansion pack passed: {status['expansion_packs']['quoted_forbidden_phrase_controller_review_adversarial'].get('passed')}",
            f"- Multilingual forbidden-phrase scope expansion pack passed: {status['expansion_packs']['multilingual_forbidden_phrase_scope_adversarial'].get('passed')}",
            f"- External review overclaim residual expansion pack passed: {status['expansion_packs']['external_review_overclaim_residual_adversarial'].get('passed')}",
            f"- External review rule-replacement residual expansion pack passed: {status['expansion_packs']['external_review_rule_replacement_residual_adversarial'].get('passed')}",
            f"- Optional clean-empty release-boundary expansion pack passed: {status['expansion_packs']['optional_clean_empty_release_boundary_adversarial'].get('passed')}",
            f"- Clean-empty residual-overclaim boundary expansion pack passed: {status['expansion_packs']['clean_empty_residual_overclaim_boundary_adversarial'].get('passed')}",
            f"- NoTargetRead closure-authority residual expansion pack passed: {status['expansion_packs']['no_target_read_closure_authority_residual_adversarial'].get('passed')}",
            f"- Authority-transfer deployment residual expansion pack passed: {status['expansion_packs']['authority_transfer_deployment_residual_adversarial'].get('passed')}",
            f"- Controller-rescue proof/deployment residual expansion pack passed: {status['expansion_packs']['controller_rescue_proof_deployment_residual_adversarial'].get('passed')}",
            f"- Clean-empty external-evidence authority-boundary expansion pack passed: {status['expansion_packs']['clean_empty_external_evidence_authority_boundary_adversarial'].get('passed')}",
            f"- Code clean-empty rule-replacement deployment residual expansion pack passed: {status['expansion_packs']['code_clean_empty_rule_replacement_deployment_residual_adversarial'].get('passed')}",
            f"- Guarded-code evidence rule-replacement overclaim residual expansion pack passed: {status['expansion_packs']['guarded_code_evidence_rule_replacement_overclaim_residual_adversarial'].get('passed')}",
            f"- Code evidence CI/failure-ledger overclaim residual expansion pack passed: {status['expansion_packs']['code_evidence_ci_failure_ledger_overclaim_residual_adversarial'].get('passed')}",
            f"- CI-completion guarded-summary failure-ledger residual expansion pack passed: {status['expansion_packs']['ci_completion_guarded_summary_failure_ledger_residual_adversarial'].get('passed')}",
            f"- Release-note noncompletion-state overclaim residual expansion pack passed: {status['expansion_packs']['release_note_noncompletion_state_overclaim_residual_adversarial'].get('passed')}",
            f"- Guarded controller-rescue release-completion overclaim residual expansion pack passed: {status['expansion_packs']['guarded_controller_rescue_release_completion_overclaim_residual_adversarial'].get('passed')}",
            f"- PSM rescue engineering-proof CI/rollback overclaim residual expansion pack passed: {status['expansion_packs']['psm_rescue_engineering_proof_ci_rollback_overclaim_residual_adversarial'].get('passed')}",
            f"- PSM rescue release-completion review-state overclaim residual expansion pack passed: {status['expansion_packs']['psm_rescue_release_completion_review_state_overclaim_residual_adversarial'].get('passed')}",
            f"- Clean-empty review-state release-authority residual expansion pack passed: {status['expansion_packs']['clean_empty_review_state_release_authority_residual_adversarial'].get('passed')}",
            f"- Clean-external-candidate writing-overclaim rescue expansion pack passed: {status['expansion_packs']['clean_external_candidate_writing_overclaim_rescue_adversarial'].get('passed')}",
            f"- Negated universal-safety clean-candidate rescue expansion pack passed: {status['expansion_packs']['negated_universal_safety_clean_candidate_rescue_adversarial'].get('passed')}",
            f"- Clean-empty negated-safety release-boundary expansion pack passed: {status['expansion_packs']['clean_empty_negated_safety_release_boundary_adversarial'].get('passed')}",
            f"- Clean-empty external-refresh completion-boundary expansion pack passed: {status['expansion_packs']['clean_empty_external_refresh_completion_boundary_adversarial'].get('passed')}",
            f"- Code go-live controller-rescue external-refresh boundary expansion pack passed: {status['expansion_packs']['code_go_live_controller_rescue_external_refresh_boundary_adversarial'].get('passed')}",
            f"- Code go-live guarantee-variant rescue boundary expansion pack passed: {status['expansion_packs']['code_go_live_guarantee_variant_rescue_boundary_adversarial'].get('passed')}",
            f"- Clean-empty go-live variant release-boundary expansion pack passed: {status['expansion_packs']['clean_empty_go_live_variant_release_boundary_adversarial'].get('passed')}",
            f"- Clean-empty controller-rescue release-completion boundary expansion pack passed: {status['expansion_packs']['clean_empty_controller_rescue_release_completion_boundary_adversarial'].get('passed')}",
            f"- Code controller-rescue rollback/production-ready residual expansion pack passed: {status['expansion_packs']['code_controller_rescue_rollback_production_ready_residual_adversarial'].get('passed')}",
            f"- Code monitoring-omission controller-rescue residual expansion pack passed: {status['expansion_packs']['code_monitoring_omission_controller_rescue_residual_adversarial'].get('passed')}",
            f"- Clean-empty monitoring/observability release-boundary expansion pack passed: {status['expansion_packs']['clean_empty_monitoring_observability_release_boundary_adversarial'].get('passed')}",
            f"- Clean-empty alert-suppression controller-rescue residual expansion pack passed: {status['expansion_packs']['clean_empty_alert_suppression_controller_rescue_residual_adversarial'].get('passed')}",
            f"- Medical alert-rescue patient-safety residual expansion pack passed: {status['expansion_packs']['medical_alert_rescue_patient_safety_residual_adversarial'].get('passed')}",
            f"- Clean-empty medical alert-rescue release-boundary expansion pack passed: {status['expansion_packs']['clean_empty_medical_alert_rescue_release_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical release-authority boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_release_authority_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical ordinary-risk visibility boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_ordinary_risk_visibility_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical meta-language boundary-phrase expansion pack passed: {status['expansion_packs']['clean_external_medical_meta_language_boundary_phrase_adversarial'].get('passed')}",
            f"- Clean-external medical future-refresh meta-boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_future_refresh_meta_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical controller-changed review-boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_controller_changed_review_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical auxiliary-evidence release-boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_auxiliary_evidence_release_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical release-summary authority-transfer boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_release_summary_authority_transfer_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical owner-signoff release-boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_owner_signoff_release_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical public-safety deployment-boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_public_safety_deployment_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical deployment-summary future-refresh boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_deployment_summary_future_refresh_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical post-release monitoring incident-free boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_post_release_monitoring_incident_free_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical patient-facing assurance regulatory-boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_patient_facing_assurance_regulatory_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical liability-release overclaim rescue-boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_liability_release_overclaim_rescue_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical liability empty-fixture compliance-closure boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_liability_empty_fixture_compliance_closure_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical regulatory-acceptance overclaim rescue-boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_regulatory_acceptance_overclaim_rescue_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical regulatory-acceptance empty-fixture authorization-closure boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_regulatory_acceptance_empty_fixture_authorization_closure_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical authorization-closure empty-fixture deployment-permission boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_authorization_closure_empty_fixture_deployment_permission_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical deployment-permission empty-fixture operational-rollout boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_deployment_permission_empty_fixture_operational_rollout_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical operational-rollout empty-fixture postmarket-monitoring boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_operational_rollout_empty_fixture_postmarket_monitoring_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical postmarket-monitoring empty-fixture surveillance-closure boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_postmarket_monitoring_empty_fixture_surveillance_closure_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical surveillance-closure empty-fixture recall-free boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_surveillance_closure_empty_fixture_recall_free_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical recall-free empty-fixture field-action-closure boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_recall_free_empty_fixture_field_action_closure_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical field-action-closure empty-fixture corrective-action boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_field_action_closure_empty_fixture_corrective_action_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical corrective-action empty-fixture remediation-closure boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_corrective_action_empty_fixture_remediation_closure_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical remediation-closure controller-rescue release-authority boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_remediation_closure_controller_rescue_release_authority_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical release-authority empty-fixture post-rescue monitoring boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_release_authority_empty_fixture_post_rescue_monitoring_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical post-rescue monitoring empty-fixture external-refresh authority boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_post_rescue_monitoring_empty_fixture_external_refresh_authority_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical external-refresh controller-rescue authority-closure boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_external_refresh_controller_rescue_authority_closure_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical authority-closure empty-fixture future-judging boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_authority_closure_empty_fixture_future_judging_boundary_adversarial'].get('passed')}",
            f"- Clean-external medical future-judging empty-fixture surveillance boundary expansion pack passed: {status['expansion_packs']['clean_external_medical_future_judging_empty_fixture_surveillance_boundary_adversarial'].get('passed')}",
            "",
            "## Next Stage",
            "",
            f"- Version: {status['next_stage']['version']}",
            f"- Objective: {status['next_stage']['objective']}",
            f"- Requires user input: {status['next_stage']['requires_user_input']}",
        ]
    )


if __name__ == "__main__":
    main()
