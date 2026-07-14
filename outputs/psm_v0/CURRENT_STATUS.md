# PSM Current Status

## Current Version

`PSM V0.252`

The current project status is `psm_v0.252`. V0.252 promotes the stable internal chat-product gate while retaining `psm_v0.251` as the formal 2228-record core evidence source. Required/fault candidate gating covers 1975 cases with gated PSM unsafe/risky at 0.

## Latest Completed Result

- Added explicit generating phases, elapsed time, cancellation, a 70-second client timeout, retry, and failure recovery.
- Failed or cancelled turns preserve the user's input; retry does not duplicate the user message.
- Audited answers are progressively displayed without putting hidden audit fields in the main conversation.
- Debug evidence is closed by default and isolated from the user-facing message log.
- Added Enter submission, Escape cancellation, focus control, ARIA live regions, and accessible labels.
- Added reproducible Playwright regression through `npm` and `make`.
- Desktop regression: no duplicate messages, layout overflow=0, console errors=0.
- Mobile regression at 390x844: layout overflow=0, primary controls remain inside the viewport, console errors=0.
- Real `qwen3.5:9b` backend UI smoke passed on the Docker runtime at `http://127.0.0.1:8766`.
- Docker runtime uses the selected 9B model and a 60-second server timeout.
- Product promotion evidence: `runtime/v0_252_product_checkpoint.json` and `runtime/v0_252_product_promotion_manifest.json`.
- External user trial and rule replacement remain closed.

## Next Stage

`PSM V0.253`

Replace route labels with executable evidence adapters:

- define a uniform route-result, provenance, and failure-ledger contract;
- connect project questions to local structured status;
- connect factual questions to source/retrieval evidence;
- connect code questions to real static checks, tests, and sandboxed commands;
- connect file questions to real file reads and citations;
- inject tool failures and conflicts so language cannot hide missing evidence or bypass PSM gating.

- Blocked: false.
- Requires user input: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.252_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- Product checkpoint: `runtime/v0_252_product_checkpoint.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
