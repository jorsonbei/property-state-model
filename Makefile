PYTHON ?= python3
NPM ?= npm
PSM_ROOT := outputs/psm_v0

.PHONY: check test serve inventory sync-runtime route-v253-eval route-v253-docker state-v254-eval state-v254-docker alpha-v255-eval alpha-v255-docker annotation-v256-eval annotation-v256-docker encoder-v257-eval encoder-v257-docker calibrate-v258-eval calibrate-v258-docker browser-install browser-regression browser-regression-real browser-regression-v253 browser-regression-v254 browser-regression-v255 browser-regression-v256 browser-regression-v257 browser-regression-v258 judge-v251-external judge-v251-external-c judge-v251-external-d judge-v251-external-e judge-v251-external-f judge-v251-external-g docker-config docker-build docker-up

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
