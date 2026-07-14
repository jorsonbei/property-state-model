# 物性AI Chat Alpha 0.252

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

- `/api/status` reports the latest project status, currently `PSM V0.252`.
- `/api/chat` preserves user and assistant roles across multi-turn history.
- Project status and roadmap answers are grounded in the local structured status.
- Relevance and grounding are audited separately from candidate safety.
- The provider contract exposes answer, grounded facts, uncertainties, required judges, model, latency, and fallback state separately.
- `qwen3.5:9b` is the current local default selected by the frozen V0.251 model comparison and independent chat gate; deterministic fallback remains mandatory.
- The default UI is normal chat: user asks, assistant answers.
- Generation phases, cancellation, timeout, preserved-input retry, and progressive answer display are enabled.
- PSM state chain, ordinary output, gated output, release boundary, evidence, and history are kept behind the debug details panel.

Browser regression:

```bash
make browser-install
make browser-regression
PSM_BASE_URL=http://127.0.0.1:8765 make browser-regression-real
```
