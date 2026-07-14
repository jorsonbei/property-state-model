PYTHON ?= python3
PSM_ROOT := outputs/psm_v0

.PHONY: check test serve inventory sync-runtime judge-v251-external docker-config docker-build docker-up

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

judge-v251-external:
	PYTHONPATH=$(PSM_ROOT) $(PYTHON) -m psm_v0.external_semantic_judge \
		--csv $(PSM_ROOT)/runtime/v0_251_external_judge_gemini_pro.csv \
		--answers $(PSM_ROOT)/runtime/v0_251_external_judge_input_answers.json \
		--prompts $(PSM_ROOT)/benchmarks/v0_251_chat_prompts.json \
		--provenance $(PSM_ROOT)/runtime/v0_251_external_judge_provenance.json \
		--out $(PSM_ROOT)/runtime/v0_251_external_semantic_judge.json

docker-config:
	docker compose config

docker-build: sync-runtime
	docker compose build

docker-up: sync-runtime
	docker compose up --build
