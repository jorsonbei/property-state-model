# 物性AI Chat Alpha 0.4

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

- `/api/status` reports the latest project status, currently `PSM V0.249`.
- `/api/chat` preserves user and assistant roles across multi-turn history.
- Project status and roadmap answers are grounded in the local structured status.
- Relevance and grounding are audited separately from candidate safety.
- The default UI is normal chat: user asks, assistant answers.
- PSM state chain, ordinary output, gated output, release boundary, evidence, and history are kept behind the debug details panel.
