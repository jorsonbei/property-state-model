PYTHON ?= python3
PSM_ROOT := outputs/psm_v0

.PHONY: check test serve inventory sync-runtime docker-config docker-build docker-up

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

docker-config:
	docker compose config

docker-build: sync-runtime
	docker compose build

docker-up: sync-runtime
	docker compose up --build
