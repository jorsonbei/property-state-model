# 物性AI Chat Alpha 0.254

Local normal-chat demo backed by the latest PSM pipeline status.

Run:

```bash
python3 outputs/psm_v0/product_alpha_app/server.py --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

Boundary:

- Internal local chat demo only.
- Not external-user trial approval.
- Not medical, legal, trading, or production release authority.
- Session memory is not consent or release authority.
- Rule replacement remains off.

Verified scope:

- `/api/status` reports the latest project status, currently `PSM V0.254`.
- `/api/chat` preserves user and assistant roles across multi-turn history.
- Project status and roadmap answers are grounded in the local structured status.
- Relevance and grounding are audited separately from candidate safety.
- The provider contract exposes answer, grounded facts, uncertainties, required judges, model, latency, and fallback state separately.
- `qwen3.5:9b` is the current local default selected by the frozen V0.251 model comparison and independent chat gate; deterministic fallback remains mandatory.
- The default UI is normal chat: user asks, assistant answers.
- Generation phases, cancellation, timeout, preserved-input retry, and progressive answer display are enabled.
- `/api/chat` exposes executable route evidence separately from the normal answer: adapter, status, facts, sources, provenance, timing, failures, and unresolved judges.
- `/api/chat` returns a task-level Pi graph with known, inferred, unknown, conflicting, and pending state plus an explainable delta from the previous turn.
- Client-supplied prior graphs are delta references only and never become evidence; failure candidates remain quarantined from blind sets and training truth.
- File reads are project-confined and read-only; code execution is limited to fixed verifier commands, while inline Python receives AST parsing only.
- PSM state chain, ordinary output, gated output, release boundary, evidence, and history are kept behind the debug details panel.

Browser regression:

```bash
make browser-install
make browser-regression
PSM_BASE_URL=http://127.0.0.1:8765 make browser-regression-real
make route-v253-eval
make state-v254-eval
```
