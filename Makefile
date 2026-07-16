PYTHON ?= python3
NPM ?= npm
PSM_ROOT := outputs/psm_v0

.PHONY: check test serve inventory sync-runtime route-v253-eval route-v253-docker state-v254-eval state-v254-docker alpha-v255-eval alpha-v255-docker annotation-v256-eval annotation-v256-docker encoder-v257-eval encoder-v257-docker calibrate-v258-eval calibrate-v258-docker sigma-v259-eval sigma-v259-docker readiness-v260-review readiness-v260-docker repair-v261-eval judge-v261-openai promote-v261 external-v261-docker protocol-v262-eval judge-v262-openai promote-v262 external-v262-docker prepare-v263 enrollment-v263-eval enrollment-v263-docker enrollment-v263-completed-docker promote-v263 pilot-v264-eval pilot-v264-docker promote-v264 quality-v265-eval quality-v265-docker promote-v265 adversarial-v266-eval adversarial-v266-docker promote-v266 prepare-v267 repair-v267-external judge-v267-openai external-v267-docker promote-v267 task-v268-eval task-v268-docker promote-v268 stability-v269-eval stability-v269-docker promote-v269 multiturn-v270-eval multiturn-v270-docker promote-v270 prepare-v271 judge-v271-openai repair-v271-local authorize-v271-rejudge rejudge-v271-openai finalize-v271 promote-v271 long-context-v272-eval long-context-v272-docker promote-v272 prepare-v273 authorize-v273 judge-v273-openai promote-v273 open-context-v274-eval open-context-v274-docker promote-v274 prepare-v275 authorize-v275 judge-v275-openai repair-v275-local authorize-v275-rejudge rejudge-v275-openai repair-v275-rejudge-local authorize-v275-attempt-3 judge-v275-attempt-3-openai promote-v275 build-v276 long-horizon-v276-eval long-horizon-v276-docker promote-v276 prepare-v277 judge-v277-openai promote-v277 build-v278 stress-v278-eval stress-v278-docker promote-v278 prepare-v279 judge-v279-openai promote-v279 build-v280 baseline-v280 rolling-v280-eval rolling-v280-docker promote-v280 isolation-v281-eval prepare-v281 judge-v281-openai promote-v281 browser-v282-rolling promote-v282 build-v283 baseline-v283 recovery-v283-eval runtime-v283-restart browser-v283-recovery promote-v283 prepare-v284 judge-v284-openai promote-v284 build-v285 baseline-v285 integrity-v285-eval integrity-v285-runtime promote-v285 build-v286 baseline-v286 recovery-v286-eval promote-v286 prepare-v287 judge-v287-openai promote-v287 runtime-v288-parity promote-v288 browser-v289-recovery promote-v289 build-v290 latency-v290-eval promote-v290 browser-v291-cancel promote-v291 browser-install browser-regression browser-regression-real browser-regression-v253 browser-regression-v254 browser-regression-v255 browser-regression-v256 browser-regression-v257 browser-regression-v258 browser-regression-v259 browser-regression-v260 browser-regression-v261 browser-regression-v262 browser-regression-v263-enrollment browser-regression-v263-completed browser-regression-v264-completed browser-regression-v265-quality browser-regression-v266-adversarial browser-regression-v267-external browser-regression-v268-task browser-regression-v269-stability browser-regression-v270-multiturn browser-regression-v272-long-context browser-regression-v274-open-context judge-v251-external judge-v251-external-c judge-v251-external-d judge-v251-external-e judge-v251-external-f judge-v251-external-g docker-config docker-build docker-up

check:
	$(PYTHON) scripts/verify_project.py

test:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) -m unittest discover -s tests -v

serve:
	$(PYTHON) $(PSM_ROOT)/product_alpha_app/server.py --host 127.0.0.1 --port 8765

inventory:
	$(PYTHON) scripts/build_artifact_inventory.py

sync-runtime:
	$(PYTHON) scripts/sync_runtime_snapshot.py

route-v253-eval:
	$(PYTHON) scripts/evaluate_v0_253_routes.py

route-v253-docker:
	$(PYTHON) scripts/verify_v0_253_docker.py

state-v254-eval:
	$(PYTHON) scripts/evaluate_v0_254_state_graph.py

state-v254-docker:
	$(PYTHON) scripts/verify_v0_254_docker.py

alpha-v255-eval:
	$(PYTHON) scripts/evaluate_v0_255_internal_alpha.py

alpha-v255-docker:
	$(PYTHON) scripts/verify_v0_255_docker.py

annotation-v256-eval:
	$(PYTHON) scripts/evaluate_v0_256_annotation_contract.py

annotation-v256-docker:
	$(PYTHON) scripts/verify_v0_256_docker.py

encoder-v257-eval:
	$(PYTHON) scripts/evaluate_v0_257_shadow_encoder.py

encoder-v257-docker:
	$(PYTHON) scripts/verify_v0_257_docker.py

calibrate-v258-eval:
	$(PYTHON) scripts/evaluate_v0_258_calibrated_shadow.py

calibrate-v258-docker:
	$(PYTHON) scripts/verify_v0_258_docker.py

sigma-v259-eval:
	$(PYTHON) scripts/evaluate_v0_259_sigma_plus.py

sigma-v259-docker:
	$(PYTHON) scripts/verify_v0_259_docker.py

readiness-v260-review:
	$(PYTHON) scripts/review_v0_260_internal_readiness.py

readiness-v260-docker:
	$(PYTHON) scripts/verify_v0_260_docker.py

repair-v261-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_261_annotation_contract_repair.py

judge-v261-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_261_openai_contract_judge.py

promote-v261:
	$(PYTHON) scripts/promote_v0_261_external_contract.py

external-v261-docker:
	$(PYTHON) scripts/verify_v0_261_docker.py

protocol-v262-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_262_external_trial_protocol.py

judge-v262-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_262_openai_protocol_judge.py

promote-v262:
	$(PYTHON) scripts/promote_v0_262_external_trial_protocol.py

external-v262-docker:
	$(PYTHON) scripts/verify_v0_262_docker.py

prepare-v263:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/prepare_v0_263_participant_enrollment.py

enrollment-v263-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_263_completed_enrollment.py

enrollment-v263-docker:
	$(PYTHON) scripts/verify_v0_263_enrollment_boundary.py

enrollment-v263-completed-docker:
	$(PYTHON) scripts/verify_v0_263_completed_enrollment_docker.py

promote-v263:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_263_participant_enrollment.py

pilot-v264-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_264_supervised_pilot.py

pilot-v264-docker:
	$(PYTHON) scripts/verify_v0_264_supervised_pilot_docker.py

promote-v264:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_264_supervised_pilot.py

quality-v265-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_265_automated_quality.py

quality-v265-docker:
	$(PYTHON) scripts/verify_v0_265_automated_quality_docker.py

promote-v265:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_265_automated_quality.py

adversarial-v266-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_266_adversarial_metamorphic.py

adversarial-v266-docker:
	$(PYTHON) scripts/verify_v0_266_adversarial_metamorphic_docker.py

promote-v266:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_266_adversarial_metamorphic.py

prepare-v267:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_267_external_adversarial_package.py

repair-v267-external:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_267_external_findings_repair.py

judge-v267-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_267_openai_adversarial_judge.py

external-v267-docker:
	$(PYTHON) scripts/verify_v0_267_external_adversarial_docker.py

promote-v267:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_267_external_adversarial.py

task-v268-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_268_task_completion.py

task-v268-docker:
	$(PYTHON) scripts/verify_v0_268_task_completion_docker.py

promote-v268:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_268_task_completion.py

stability-v269-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_269_task_stability.py

stability-v269-docker:
	$(PYTHON) scripts/verify_v0_269_task_stability_docker.py

promote-v269:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_269_task_stability.py

multiturn-v270-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_270_multiturn_constraints.py

multiturn-v270-docker:
	$(PYTHON) scripts/verify_v0_270_multiturn_docker.py

promote-v270:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_270_multiturn_constraints.py

prepare-v271:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_271_external_multiturn_package.py

judge-v271-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_271_openai_multiturn_judge.py

repair-v271-local:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_271_external_findings_repair.py

authorize-v271-rejudge:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/authorize_v0_271_external_multiturn_rejudge.py

rejudge-v271-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_271_openai_multiturn_judge.py \
		--package $(PSM_ROOT)/runtime/v0_271_external_multiturn_rejudge_package.json \
		--out $(PSM_ROOT)/runtime/v0_271_openai_external_multiturn_rejudge.json

finalize-v271:
	$(PYTHON) scripts/finalize_v0_271_external_multiturn_rejudge.py

promote-v271:
	$(PYTHON) scripts/promote_v0_271_external_multiturn.py

long-context-v272-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_272_long_context_state.py

long-context-v272-docker:
	$(PYTHON) scripts/verify_v0_272_long_context_docker.py

promote-v272:
	$(PYTHON) scripts/promote_v0_272_long_context_state.py

prepare-v273:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_273_external_long_context_package.py

authorize-v273:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/authorize_v0_273_external_long_context_review.py

judge-v273-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_273_openai_long_context_judge.py

promote-v273:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_273_external_long_context.py

open-context-v274-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_274_open_context_generalization.py

open-context-v274-docker:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/verify_v0_274_open_context_docker.py

promote-v274:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_274_open_context_generalization.py

prepare-v275:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_275_external_open_context_package.py

authorize-v275:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/authorize_v0_275_external_open_context_review.py

judge-v275-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_275_openai_open_context_judge.py

repair-v275-local:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_275_external_findings_repair.py

authorize-v275-rejudge:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/authorize_v0_275_external_open_context_rejudge.py

rejudge-v275-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_275_openai_open_context_judge.py \
		--package $(PSM_ROOT)/runtime/v0_275_external_open_context_rejudge_package.json \
		--out $(PSM_ROOT)/runtime/v0_275_openai_external_open_context_rejudge.json

repair-v275-rejudge-local:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_275_external_rejudge_findings_repair.py

authorize-v275-attempt-3:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/authorize_v0_275_external_open_context_review_attempt_3.py

judge-v275-attempt-3-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_275_openai_open_context_judge.py \
		--package $(PSM_ROOT)/runtime/v0_275_external_open_context_review_attempt_3_package.json \
		--out $(PSM_ROOT)/runtime/v0_275_openai_external_open_context_judge_attempt_3.json

promote-v275:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_275_external_open_context.py

build-v276:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_276_long_horizon_state_compression_contract.py

long-horizon-v276-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_276_long_horizon_state_compression.py

long-horizon-v276-docker:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/verify_v0_276_long_horizon_docker.py

promote-v276:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_276_long_horizon_state_compression.py

prepare-v277:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_277_external_state_compression_review.py

judge-v277-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_277_openai_state_compression_judge.py

promote-v277:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_277_external_state_compression.py

build-v278:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_278_incremental_long_horizon_stress_contract.py

stress-v278-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_278_incremental_long_horizon_stress.py

stress-v278-docker:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/verify_v0_278_incremental_long_horizon_docker.py

promote-v278:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_278_incremental_long_horizon_stress.py

prepare-v279:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_279_external_incremental_stress_review.py

judge-v279-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_279_openai_incremental_stress_judge.py

promote-v279:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_279_external_incremental_stress.py

build-v280:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_280_rolling_state_handoff_contract.py

baseline-v280:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/capture_v0_280_window_truncation_baseline.py

rolling-v280-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_280_rolling_state_handoff.py

rolling-v280-docker:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/verify_v0_280_rolling_state_handoff_docker.py

promote-v280:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_280_rolling_state_handoff.py

isolation-v281-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_281_rolling_state_isolation.py

prepare-v281:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_281_external_rolling_state_review.py

judge-v281-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_281_openai_rolling_state_judge.py

promote-v281:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_281_external_rolling_state.py

browser-v282-rolling:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} node scripts/browser_regression_v282_rolling_state_lifecycle.cjs

promote-v282:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_282_rolling_state_browser_lifecycle.py

build-v283:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_283_restart_recovery_contract.py

baseline-v283:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/capture_v0_283_restart_recovery_baseline.py

recovery-v283-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_283_restart_recovery.py

runtime-v283-restart:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/verify_v0_283_controlled_restart.py

browser-v283-recovery:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} node scripts/browser_regression_v283_restart_recovery.cjs

promote-v283:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_283_restart_recovery.py
	$(MAKE) sync-runtime

prepare-v284:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_284_external_restart_recovery_review.py

judge-v284-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_284_openai_restart_recovery_judge.py

promote-v284:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_284_external_restart_recovery.py
	$(MAKE) sync-runtime

build-v285:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_285_lifecycle_signal_integrity_contract.py

baseline-v285:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/capture_v0_285_lifecycle_signal_integrity_baseline.py

integrity-v285-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_285_lifecycle_signal_integrity.py

integrity-v285-runtime:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/verify_v0_285_host_docker_integrity.py

promote-v285:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_285_lifecycle_signal_integrity.py
	$(MAKE) sync-runtime

build-v286:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_286_natural_recovery_reference_contract.py

baseline-v286:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/capture_v0_286_natural_recovery_reference_baseline.py

recovery-v286-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_286_natural_recovery_reference.py

promote-v286:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_286_natural_recovery_reference.py
	$(MAKE) sync-runtime

prepare-v287:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_287_external_natural_recovery_review.py

judge-v287-openai:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_287_openai_natural_recovery_judge.py

promote-v287:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_287_external_natural_recovery.py
	$(MAKE) sync-runtime

runtime-v288-parity:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/verify_v0_288_host_docker_natural_recovery.py

promote-v288:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_288_runtime_natural_recovery.py
	$(MAKE) sync-runtime

browser-v289-recovery:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} node scripts/browser_regression_v289_natural_recovery.cjs

promote-v289:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_289_browser_natural_recovery.py
	$(MAKE) sync-runtime

build-v290:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/build_v0_290_latency_budget_contract.py

latency-v290-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_290_latency_budget.py

promote-v290:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_290_latency_budget.py
	$(MAKE) sync-runtime

browser-v291-cancel:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} node scripts/browser_regression_v291_cancel_retry.cjs

promote-v291:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/promote_v0_291_cancel_retry.py
	$(MAKE) sync-runtime

browser-install:
	$(NPM) install
	$(NPM) exec playwright install chromium

browser-regression:
	$(NPM) run browser-regression

browser-regression-real:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} PSM_BROWSER_REAL_CHAT=1 $(NPM) run browser-regression

browser-regression-v253:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	PSM_BROWSER_OUTDIR=$(PSM_ROOT)/runtime/v0_253_browser_regression \
	PSM_BROWSER_SCHEMA=psm_v0_253_browser_regression_v1 \
	PSM_BROWSER_REAL_CHAT=1 PSM_BROWSER_ROUTE_EVIDENCE=1 \
	$(NPM) run browser-regression

browser-regression-v254:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	PSM_BROWSER_OUTDIR=$(PSM_ROOT)/runtime/v0_254_browser_regression \
	PSM_BROWSER_SCHEMA=psm_v0_254_browser_regression_v1 \
	PSM_BROWSER_REAL_CHAT=1 PSM_BROWSER_ROUTE_EVIDENCE=1 \
	$(NPM) run browser-regression

browser-regression-v255:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	PSM_BROWSER_OUTDIR=$(PSM_ROOT)/runtime/v0_255_browser_regression \
	PSM_BROWSER_SCHEMA=psm_v0_255_browser_regression_v1 \
	PSM_BROWSER_REAL_CHAT=1 PSM_BROWSER_ROUTE_EVIDENCE=1 \
	PSM_BROWSER_EXPECT_INTERNAL_READY=1 \
	PSM_BROWSER_STATUS_VERSION="PSM V0.255" \
	$(NPM) run browser-regression

browser-regression-v256:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	PSM_BROWSER_OUTDIR=$(PSM_ROOT)/runtime/v0_256_browser_regression \
	PSM_BROWSER_SCHEMA=psm_v0_256_browser_regression_v1 \
	PSM_BROWSER_REAL_CHAT=1 PSM_BROWSER_ROUTE_EVIDENCE=1 \
	PSM_BROWSER_EXPECT_INTERNAL_READY=1 \
	PSM_BROWSER_STATUS_VERSION="PSM V0.256" \
	$(NPM) run browser-regression

browser-regression-v257:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	PSM_BROWSER_OUTDIR=$(PSM_ROOT)/runtime/v0_257_browser_regression \
	PSM_BROWSER_SCHEMA=psm_v0_257_browser_regression_v1 \
	PSM_BROWSER_REAL_CHAT=1 PSM_BROWSER_ROUTE_EVIDENCE=1 \
	PSM_BROWSER_EXPECT_INTERNAL_READY=1 \
	PSM_BROWSER_STATUS_VERSION="PSM V0.257" \
	$(NPM) run browser-regression

browser-regression-v258:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	PSM_BROWSER_OUTDIR=$(PSM_ROOT)/runtime/v0_258_browser_regression \
	PSM_BROWSER_SCHEMA=psm_v0_258_browser_regression_v1 \
	PSM_BROWSER_REAL_CHAT=1 PSM_BROWSER_ROUTE_EVIDENCE=1 \
	PSM_BROWSER_EXPECT_INTERNAL_READY=1 \
	PSM_BROWSER_STATUS_VERSION="PSM V0.258" \
	$(NPM) run browser-regression

browser-regression-v259:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	PSM_BROWSER_OUTDIR=$(PSM_ROOT)/runtime/v0_259_browser_regression \
	PSM_BROWSER_SCHEMA=psm_v0_259_browser_regression_v1 \
	PSM_BROWSER_REAL_CHAT=1 PSM_BROWSER_ROUTE_EVIDENCE=1 \
	PSM_BROWSER_EXPECT_INTERNAL_READY=1 \
	PSM_BROWSER_STATUS_VERSION="PSM V0.259" \
	$(NPM) run browser-regression

browser-regression-v260:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	PSM_BROWSER_OUTDIR=$(PSM_ROOT)/runtime/v0_260_browser_regression \
	PSM_BROWSER_SCHEMA=psm_v0_260_browser_regression_v1 \
	PSM_BROWSER_REAL_CHAT=1 PSM_BROWSER_ROUTE_EVIDENCE=1 \
	PSM_BROWSER_EXPECT_INTERNAL_READY=1 \
	PSM_BROWSER_STATUS_VERSION="PSM V0.260" \
	$(NPM) run browser-regression

browser-regression-v261:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	PSM_BROWSER_OUTDIR=$(PSM_ROOT)/runtime/v0_261_browser_regression \
	PSM_BROWSER_SCHEMA=psm_v0_261_browser_regression_v1 \
	PSM_BROWSER_REAL_CHAT=1 PSM_BROWSER_ROUTE_EVIDENCE=1 \
	PSM_BROWSER_EXPECT_INTERNAL_READY=1 \
	PSM_BROWSER_STATUS_VERSION="PSM V0.261" \
	$(NPM) run browser-regression

browser-regression-v262:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	PSM_BROWSER_OUTDIR=$(PSM_ROOT)/runtime/v0_262_browser_regression \
	PSM_BROWSER_SCHEMA=psm_v0_262_browser_regression_v1 \
	PSM_BROWSER_REAL_CHAT=1 PSM_BROWSER_ROUTE_EVIDENCE=1 \
	PSM_BROWSER_EXPECT_INTERNAL_READY=1 \
	PSM_BROWSER_STATUS_VERSION="PSM V0.262" \
	$(NPM) run browser-regression

browser-regression-v263-enrollment:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v263_enrollment.cjs

browser-regression-v263-completed:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v263_completed_enrollment.cjs

browser-regression-v264-completed:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v264_supervised_pilot.cjs

browser-regression-v265-quality:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v265_automated_quality.cjs

browser-regression-v266-adversarial:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v266_adversarial_metamorphic.cjs

browser-regression-v267-external:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v267_external_adversarial.cjs

browser-regression-v268-task:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v268_task_completion.cjs

browser-regression-v269-stability:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v269_stability_recovery.cjs

browser-regression-v270-multiturn:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v270_multiturn.cjs

browser-regression-v272-long-context:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v272_long_context.cjs

browser-regression-v274-open-context:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v274_open_context.cjs

judge-v251-external: judge-v251-external-c judge-v251-external-d judge-v251-external-e judge-v251-external-f judge-v251-external-g

judge-v251-external-c:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) -m psm_v0.external_semantic_judge \
		--csv $(PSM_ROOT)/runtime/v0_251_external_judge_gemini_pro.csv \
		--answers $(PSM_ROOT)/runtime/v0_251_external_judge_input_answers.json \
		--prompts $(PSM_ROOT)/benchmarks/v0_251_chat_prompts.json \
		--provenance $(PSM_ROOT)/runtime/v0_251_external_judge_provenance.json \
		--out $(PSM_ROOT)/runtime/v0_251_external_semantic_judge.json

judge-v251-external-d:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) -m psm_v0.external_semantic_judge \
		--csv $(PSM_ROOT)/runtime/v0_251_wave_d_external_judge_chatgpt_instant.csv \
		--answers $(PSM_ROOT)/runtime/v0_251_wave_d_external_judge_input_answers.json \
		--prompts $(PSM_ROOT)/benchmarks/v0_251_chat_prompts_wave_d.json \
		--provenance $(PSM_ROOT)/runtime/v0_251_wave_d_external_judge_provenance.json \
		--out $(PSM_ROOT)/runtime/v0_251_wave_d_external_semantic_judge.json

judge-v251-external-e:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) -m psm_v0.external_semantic_judge \
		--csv $(PSM_ROOT)/runtime/v0_251_wave_e_external_judge_gemini_pro.csv \
		--answers $(PSM_ROOT)/runtime/v0_251_wave_e_external_judge_input_answers.json \
		--prompts $(PSM_ROOT)/benchmarks/v0_251_chat_prompts_wave_e.json \
		--provenance $(PSM_ROOT)/runtime/v0_251_wave_e_external_judge_provenance.json \
		--out $(PSM_ROOT)/runtime/v0_251_wave_e_external_semantic_judge.json

judge-v251-external-f:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) -m psm_v0.external_semantic_judge \
		--csv $(PSM_ROOT)/runtime/v0_251_wave_f_external_judge_chatgpt_instant.csv \
		--answers $(PSM_ROOT)/runtime/v0_251_wave_f_external_judge_input_answers.json \
		--prompts $(PSM_ROOT)/benchmarks/v0_251_chat_prompts_wave_f.json \
		--provenance $(PSM_ROOT)/runtime/v0_251_wave_f_external_judge_provenance.json \
		--out $(PSM_ROOT)/runtime/v0_251_wave_f_external_semantic_judge.json

judge-v251-external-g:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) -m psm_v0.external_semantic_judge \
		--csv $(PSM_ROOT)/runtime/v0_251_wave_g_external_judge_gemini_pro.csv \
		--answers $(PSM_ROOT)/runtime/v0_251_wave_g_answers.json \
		--prompts $(PSM_ROOT)/benchmarks/v0_251_chat_prompts_wave_g.json \
		--provenance $(PSM_ROOT)/runtime/v0_251_wave_g_external_judge_provenance.json \
		--out $(PSM_ROOT)/runtime/v0_251_wave_g_external_semantic_judge.json

docker-config:
	docker compose config

docker-build: sync-runtime
	docker compose build

docker-up: sync-runtime
	docker compose up --build

.PHONY: build-v292 server-cancel-v292-eval browser-v292-cancel regression-v292 promote-v292

build-v292:
	$(PYTHON) scripts/build_v0_292_server_cancel_contract.py

server-cancel-v292-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_292_server_cancel.py

browser-v292-cancel:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v292_server_cancel.cjs

regression-v292:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_292_regression.py

promote-v292:
	$(PYTHON) scripts/promote_v0_292_server_cancel.py

.PHONY: build-v293 concurrency-v293-eval browser-v293-backpressure regression-v293 promote-v293

build-v293:
	$(PYTHON) scripts/build_v0_293_concurrency_contract.py

concurrency-v293-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_293_concurrency_backpressure.py

browser-v293-backpressure:
	PSM_BASE_URL=$${PSM_BASE_URL:-http://127.0.0.1:8765} \
	node scripts/browser_regression_v293_backpressure.cjs

regression-v293:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_293_regression.py

promote-v293:
	$(PYTHON) scripts/promote_v0_293_concurrency_backpressure.py

.PHONY: build-v294 telemetry-v294-eval regression-v294 promote-v294

build-v294:
	$(PYTHON) scripts/build_v0_294_content_free_telemetry_contract.py

telemetry-v294-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_294_content_free_telemetry.py

regression-v294:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_294_regression.py

promote-v294:
	$(PYTHON) scripts/promote_v0_294_content_free_telemetry.py

.PHONY: build-v295 deployment-v295-eval regression-v295 promote-v295

build-v295:
	$(PYTHON) scripts/build_v0_295_synthetic_deployment_contract.py

deployment-v295-eval:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/evaluate_v0_295_synthetic_deployment.py

regression-v295:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) scripts/run_v0_295_regression.py

promote-v295:
	$(PYTHON) scripts/promote_v0_295_synthetic_deployment.py
