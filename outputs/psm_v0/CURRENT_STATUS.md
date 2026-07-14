# PSM Current Status

## Current Version

`PSM V0.254`

The current project status is `psm_v0.254`. V0.254 promotes dynamic task-level Pi and eta state while retaining `psm_v0.251` as the formal 2228-record core evidence source. Required/fault candidate gating remains 1975 cases with gated PSM unsafe/risky at 0.

## Latest Completed Result

- Added `psm_task_state_graph_v1`: messages, sources, route adapters, facts, claims, unknowns, failures, and judges now form a task-level dependency graph.
- Graph nodes use five explicit states: known, inferred, unknown, conflicting, and pending.
- Stable graph identities and `psm_task_state_graph_delta_v1` explain additions, removals, updates, and state transitions when evidence changes.
- Dynamic Pi and eta summaries are projected back into each packet with node/edge counts, uncertainty counts, conflicts, pending items, and the next protocol.
- Client-supplied prior graphs are used only as delta references; they cannot introduce evidence or release authority.
- Failure-ledger events enter `psm_failure_learning_queue_v1` in quarantine. Independent screening can allow regression use only; blind-set and training-truth backflow remain sealed.
- Stage evaluation covers 4 task graphs, 10 node kinds, all 5 states, 3 graph deltas, and real project/file/code route adapters.
- Unit and integration regression currently pass 86/86 before final browser/Docker promotion.
- External user trial, arbitrary high-risk external judgment, and rule replacement remain closed.

## Next Stage

`PSM V0.255`

Run the internal chat Alpha gate:

- replay the frozen V0.251 independent blind-chat evidence;
- verify multi-turn task-state continuity, project grounding, ordinary chat, and helpful high-risk boundaries;
- require zero critical fact hallucinations and zero critical safety false negatives;
- pass API, desktop, mobile, real-backend, and Docker regressions;
- issue an internal-use decision only; keep external-user trial closed.

- Blocked: false.
- Requires user input: false.

## Recovery Artifacts

- Machine status: `project_status_out/psm_v0.254_project_status.json`.
- Public runtime snapshot: `runtime/current_runtime_snapshot.json`.
- State checkpoint: `runtime/v0_254_state_checkpoint.json`.
- Task-state evaluation: `runtime/v0_254_task_state_graph_report.json`.
- Failure-learning queue: `runtime/v0_254_failure_learning_queue.json`.
- Current execution roadmap: `roadmap_out/PSM_Full_Project_Audit_and_Execution_Roadmap_V0.248_to_V0.260.md`.

Version history is stored as independent snapshots under `status_history/`; it is never embedded recursively here.
