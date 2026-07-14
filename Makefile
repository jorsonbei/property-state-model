PYTHON ?= python3
PSM_ROOT := outputs/psm_v0

.PHONY: check test serve inventory sync-runtime judge-v251-external judge-v251-external-c judge-v251-external-d judge-v251-external-e judge-v251-external-f judge-v251-external-g docker-config docker-build docker-up

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
