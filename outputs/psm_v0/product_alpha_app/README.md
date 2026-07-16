# 物性AI Chat Alpha 0.295 / Synthetic-only Deployment

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
- The V0.262-V0.264 invite-only workflow remains historical evidence only; its active page and APIs return 410.
- V0.295 uses synthetic and automated validation only; it recruits no humans and claims no human validation.
- Not medical, legal, trading, or production release authority.
- Session memory is not consent or release authority.
- Rule replacement remains off.

Verified scope:

- `/api/status` reports the latest promoted project status, currently `PSM V0.295`, and explicitly marks the human workflow disabled.
- `/api/status` exposes `internal_trial_ready` separately from the still-closed external-user gate.
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
- The internal chat Alpha gate is ready for stable local single-user use; this is not public-service, multi-user, privacy-compliance, or professional-authority approval.
- The V0.256 annotation contract keeps Q/Omega/phi/Delta sigma/Pi/eta/B_sigma targets, disagreement, protected splits, and judge-only fields outside the normal chat feature view; training has not started and rule replacement remains closed.
- The V0.257 trainable seven-head state encoder runs as an offline shadow baseline only; it cannot control chat routing, release, or professional action, and deterministic gating remains authoritative.
- V0.258 calibrates confidence for all seven shadow heads and adds low-confidence and consensus abstention; base weights remain frozen and deterministic rules still own every runtime decision.
- V0.259 returns a `sigma_plus_delivery` packet with a natural `user_view` and a developer-only trace containing statement coverage, provenance, tools, failures, judges, state, and calibrated shadow observations.
- V0.260 confirms `internal_trial_ready` for local single-user use after replaying core, blind, Alpha, model, Sigma+, browser, Docker, failure-ledger, and residual-risk evidence.
- V0.261 repairs and independently revalidates the external annotation contract; V0.262 freezes and independently passes the conservative three-to-five-person invite-only trial protocol.
- V0.263 fixes and completes the selected three-person enrollment sequence; V0.264 completes three credited low-risk turns for each participant.
- V0.265 removes the feedback fields and endpoint, then validates 30 synthetic cases and 12 simulated roles under an explicit synthetic-only boundary.
- V0.266 preserves eight initial failures, then passes 15/15 adversarial pairs and 30/30 variants with deterministic rules and release boundaries retained.
- V0.267 retains three failed external reviews, repairs the resulting findings, then passes the final 15/15 independent semantic review.
- V0.268 retains five initial task failures and three transparent errata, then passes 21/21 translation, rewriting, extraction, comparison, summarization, planning, and explanation tasks.
- V0.269 passes 21/21 repeated task runs plus cancel, timeout, retry, offline, empty-response, browser, and Docker recovery gates.
- V0.270 retains five initial failures, then passes 12/12 multi-turn reference, topic-switch, correction-priority, and constraint-persistence cases.
- V0.271 retains the initial external M07/M08 failure and passes the separately authorized 12/12 independent rejudge after local repair.
- V0.274 retains a 0/10 first run and then passes 10/10 unseen open-context cases with a user-authoritative state capsule, plus browser and Docker boundaries.
- V0.273 is package-ready but has zero authorized API calls while the USD 24/24 synthetic budget is fully reserved.
- Sensitive or unknown participant data stops the entire trial without automatic resume. Raw prompts and answers are never persisted or submitted to external APIs.

Browser regression:

```bash
make browser-install
make browser-regression
PSM_BASE_URL=http://127.0.0.1:8765 make browser-regression-real
make route-v253-eval
make state-v254-eval
make alpha-v255-eval
make annotation-v256-eval
make encoder-v257-eval
make calibrate-v258-eval
make sigma-v259-eval
make readiness-v260-review
make quality-v265-eval
make browser-regression-v265-quality
make quality-v265-docker
make promote-v265
make adversarial-v266-eval
make browser-regression-v266-adversarial
make adversarial-v266-docker
make promote-v266
make task-v268-eval
make browser-regression-v268-task
make task-v268-docker
make promote-v268
```
