from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Iterable


GRAPH_SCHEMA = "psm_task_state_graph_v1"
DELTA_SCHEMA = "psm_task_state_graph_delta_v1"
FAILURE_QUEUE_SCHEMA = "psm_failure_learning_queue_v1"
CLAIM_STATES = {"known", "inferred", "unknown", "conflicting", "pending"}


def build_task_state_graph(
    conversation: list[dict[str, str]],
    pipeline_result: dict,
    route_execution: dict,
    *,
    previous_graph: dict | None = None,
) -> dict:
    """Build a task graph from current evidence; prior client state is delta-only."""

    packet = pipeline_result["packet"]
    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}

    task_id = _node_id("task", packet.get("domain") or "general")
    _add_node(
        nodes,
        node_id=task_id,
        kind="task",
        label=f"{packet.get('domain', 'general')} task",
        state="inferred",
        origin="state_pipeline",
    )

    previous_message_id = None
    for index, message in enumerate(conversation, start=1):
        role = str(message.get("role") or "unknown")
        content = str(message.get("content") or "").strip()
        message_id = _node_id("message", f"{index}:{role}:{content}")
        _add_node(
            nodes,
            node_id=message_id,
            kind="message",
            label=_clip(content, 160),
            state="known",
            origin=f"conversation.{role}",
            turn=index,
            metadata={"role": role, "content_sha256": _sha(content)},
        )
        _add_edge(edges, message_id, task_id, "updates_task")
        if previous_message_id:
            _add_edge(edges, previous_message_id, message_id, "precedes")
        previous_message_id = message_id

    source_ids: dict[str, str] = {}
    for source in route_execution.get("sources") or []:
        source = str(source)
        source_id = _node_id("source", source)
        source_ids[source] = source_id
        _add_node(
            nodes,
            node_id=source_id,
            kind="source",
            label=source,
            state="known",
            origin="route_execution",
        )
        _add_edge(edges, source_id, task_id, "informs_task")

    adapter_ids: dict[str, str] = {}
    for adapter in route_execution.get("adapters") or []:
        name = str(adapter.get("adapter") or "unknown_adapter")
        adapter_id = _node_id("adapter", name)
        adapter_ids[name] = adapter_id
        adapter_status = str(adapter.get("status") or "pending")
        state = "known" if adapter_status in {"success", "partial"} else "pending"
        if adapter_status == "conflict":
            state = "conflicting"
        _add_node(
            nodes,
            node_id=adapter_id,
            kind="adapter",
            label=name,
            state=state,
            origin="route_execution",
            metadata={"status": adapter_status},
        )
        _add_edge(edges, adapter_id, task_id, "executes_for")

    conflict_keys = set((route_execution.get("conflicts") or {}).keys())
    claim_nodes: dict[str, str] = {}
    for adapter in route_execution.get("adapters") or []:
        adapter_name = str(adapter.get("adapter") or "unknown_adapter")
        adapter_id = adapter_ids.get(adapter_name)
        for key, value in (adapter.get("claims") or {}).items():
            claim_key = str(key)
            claim_id = _node_id("claim", claim_key)
            claim_nodes[claim_key] = claim_id
            claim_state = "conflicting" if claim_key in conflict_keys else "known"
            _add_node(
                nodes,
                node_id=claim_id,
                kind="claim",
                label=f"{claim_key}={value}",
                state=claim_state,
                origin=adapter_name,
                metadata={"claim": claim_key, "value": str(value)},
            )
            if adapter_id:
                _add_edge(edges, adapter_id, claim_id, "produces_claim")
            _add_edge(edges, claim_id, task_id, "constrains_task")

    for index, fact in enumerate(route_execution.get("facts") or [], start=1):
        fact = str(fact)
        fact_id = _node_id("fact", fact)
        _add_node(
            nodes,
            node_id=fact_id,
            kind="fact",
            label=_clip(fact, 200),
            state="known",
            origin="route_execution",
        )
        _add_edge(edges, fact_id, task_id, "supports_task")
        for source_id in source_ids.values():
            _add_edge(edges, source_id, fact_id, "supports_fact")

    for fact in packet.get("phi_state", {}).get("facts") or []:
        fact = str(fact)
        fact_id = _node_id("inference", fact)
        _add_node(
            nodes,
            node_id=fact_id,
            kind="claim",
            label=_clip(fact, 200),
            state="inferred",
            origin="phi_state",
        )
        _add_edge(edges, fact_id, task_id, "describes_task")

    for unknown in packet.get("eta", {}).get("uncertainties") or []:
        unknown = str(unknown)
        unknown_id = _node_id("unknown", unknown)
        _add_node(
            nodes,
            node_id=unknown_id,
            kind="uncertainty",
            label=unknown,
            state="unknown",
            origin="eta",
        )
        _add_edge(edges, unknown_id, task_id, "limits_task")

    satisfied_judges = set(route_execution.get("satisfied_judges") or [])
    for judge in route_execution.get("required_judges") or []:
        judge = str(judge)
        judge_id = _node_id("judge", judge)
        state = "known" if judge in satisfied_judges else "pending"
        _add_node(
            nodes,
            node_id=judge_id,
            kind="judge",
            label=judge,
            state=state,
            origin="omega_route",
            metadata={"satisfied": judge in satisfied_judges},
        )
        _add_edge(edges, judge_id, task_id, "gates_task")

    for failure in route_execution.get("failure_events") or []:
        code = str(failure.get("code") or "route_failure")
        reason = str(failure.get("reason") or code)
        failure_id = _node_id("failure", f"{code}:{reason}")
        _add_node(
            nodes,
            node_id=failure_id,
            kind="failure",
            label=_clip(reason, 200),
            state="conflicting" if code == "evidence_conflict" else "pending",
            origin="route_failure_ledger",
            metadata={"code": code, "route": failure.get("route")},
        )
        _add_edge(edges, failure_id, task_id, "blocks_task")

    for claim, values in (route_execution.get("conflicts") or {}).items():
        claim_id = claim_nodes.get(str(claim)) or _node_id("claim", str(claim))
        if claim_id not in nodes:
            _add_node(
                nodes,
                node_id=claim_id,
                kind="claim",
                label=str(claim),
                state="conflicting",
                origin="route_execution",
            )
        for value in values:
            value_id = _node_id("conflict_value", f"{claim}:{value}")
            _add_node(
                nodes,
                node_id=value_id,
                kind="evidence_value",
                label=str(value),
                state="conflicting",
                origin="route_execution",
            )
            _add_edge(edges, value_id, claim_id, "conflicts_with")

    node_list = sorted(nodes.values(), key=lambda item: item["id"])
    edge_list = sorted(edges.values(), key=lambda item: item["id"])
    state_counts = dict(sorted(Counter(node["state"] for node in node_list).items()))
    failure_queue = build_failure_learning_queue(route_execution.get("failure_events") or [])
    graph = {
        "schema_version": GRAPH_SCHEMA,
        "graph_id": _graph_id(node_list, edge_list),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "packet_id": packet.get("packet_id"),
        "domain": packet.get("domain"),
        "nodes": node_list,
        "edges": edge_list,
        "state_counts": state_counts,
        "next_protocol": derive_next_protocol(node_list, route_execution),
        "failure_learning_queue": failure_queue,
        "boundaries": {
            "prior_client_graph_is_evidence": False,
            "automatic_blind_set_backflow": False,
            "automatic_training_truth_backflow": False,
            "external_release_authority": False,
            "rule_replacement_allowed": False,
        },
    }
    graph["delta"] = compare_task_graphs(sanitize_previous_graph(previous_graph), graph)
    return graph


def derive_next_protocol(nodes: list[dict], route_execution: dict) -> dict:
    conflicting = [node for node in nodes if node["state"] == "conflicting"]
    pending_failures = [node for node in nodes if node["kind"] == "failure"]
    pending_judges = [
        node for node in nodes if node["kind"] == "judge" and node["state"] == "pending"
    ]
    unknowns = [node for node in nodes if node["state"] == "unknown"]
    if conflicting:
        action = "resolve_evidence_conflicts"
        reason = f"{len(conflicting)} conflicting state nodes must be resolved before a stronger claim."
    elif pending_failures:
        action = "repair_route_failures"
        reason = f"{len(pending_failures)} route failures remain visible and unresolved."
    elif pending_judges:
        action = "obtain_required_judges"
        reason = f"{len(pending_judges)} required judges remain pending."
    elif unknowns:
        action = "collect_missing_evidence"
        reason = f"{len(unknowns)} task uncertainties still limit the claim."
    elif route_execution.get("can_support_strong_claim"):
        action = "compose_traceable_answer"
        reason = "Current route evidence and required judges support a traceable answer."
    else:
        action = "retain_bounded_answer"
        reason = "Current evidence supports only a bounded answer."
    return {
        "action": action,
        "reason": reason,
        "external_release_authority": False,
    }


def build_failure_learning_queue(
    events: Iterable[dict],
    *,
    independent_screening: dict[str, dict] | None = None,
) -> dict:
    screening = independent_screening or {}
    candidates = []
    for event in events:
        canonical = json.dumps(event, ensure_ascii=False, sort_keys=True)
        candidate_id = "flc_" + _sha(canonical)[:16]
        review = screening.get(candidate_id) or {}
        independently_approved = (
            review.get("decision") == "approved"
            and review.get("reviewer_independent") is True
            and bool(str(review.get("reviewer_id") or "").strip())
        )
        candidates.append(
            {
                "candidate_id": candidate_id,
                "failure_code": event.get("code"),
                "route": event.get("route"),
                "state": "screened_for_regression" if independently_approved else "quarantined_pending_screening",
                "independent_screening_required": True,
                "independent_screening_passed": independently_approved,
                "eligible_for_regression": independently_approved,
                "eligible_for_blind_set": False,
                "eligible_for_training_truth": False,
                "automatic_backflow_allowed": False,
                "source_event_sha256": _sha(canonical),
            }
        )
    return {
        "schema_version": FAILURE_QUEUE_SCHEMA,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "screened_count": sum(item["independent_screening_passed"] for item in candidates),
        "blind_set_backflow_count": 0,
        "training_truth_backflow_count": 0,
    }


def compare_task_graphs(previous: dict | None, current: dict) -> dict:
    if not previous:
        return {
            "schema_version": DELTA_SCHEMA,
            "previous_graph_id": None,
            "current_graph_id": current.get("graph_id"),
            "added_nodes": [node["id"] for node in current.get("nodes") or []],
            "removed_nodes": [],
            "changed_nodes": [],
            "added_edges": [edge["id"] for edge in current.get("edges") or []],
            "removed_edges": [],
            "state_transitions": [],
            "explanation": "Initialized the task graph from the current conversation and route evidence.",
        }
    previous_nodes = {node["id"]: node for node in previous.get("nodes") or []}
    current_nodes = {node["id"]: node for node in current.get("nodes") or []}
    previous_edges = {edge["id"]: edge for edge in previous.get("edges") or []}
    current_edges = {edge["id"]: edge for edge in current.get("edges") or []}
    added_nodes = sorted(current_nodes.keys() - previous_nodes.keys())
    removed_nodes = sorted(previous_nodes.keys() - current_nodes.keys())
    changed_nodes = sorted(
        node_id
        for node_id in current_nodes.keys() & previous_nodes.keys()
        if _stable_node(previous_nodes[node_id]) != _stable_node(current_nodes[node_id])
    )
    transitions = [
        {
            "node_id": node_id,
            "from": previous_nodes[node_id].get("state"),
            "to": current_nodes[node_id].get("state"),
        }
        for node_id in changed_nodes
        if previous_nodes[node_id].get("state") != current_nodes[node_id].get("state")
    ]
    return {
        "schema_version": DELTA_SCHEMA,
        "previous_graph_id": previous.get("graph_id"),
        "current_graph_id": current.get("graph_id"),
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "changed_nodes": changed_nodes,
        "added_edges": sorted(current_edges.keys() - previous_edges.keys()),
        "removed_edges": sorted(previous_edges.keys() - current_edges.keys()),
        "state_transitions": transitions,
        "explanation": (
            f"Task state changed: +{len(added_nodes)} nodes, -{len(removed_nodes)} nodes, "
            f"{len(changed_nodes)} updated nodes, {len(transitions)} state transitions."
        ),
    }


def sanitize_previous_graph(value: dict | None) -> dict | None:
    if not isinstance(value, dict) or value.get("schema_version") != GRAPH_SCHEMA:
        return None
    nodes = []
    for item in (value.get("nodes") or [])[:500]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        state = item.get("state") if item.get("state") in CLAIM_STATES else "unknown"
        nodes.append({**item, "state": state})
    edges = [
        item
        for item in (value.get("edges") or [])[:1000]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    return {
        "schema_version": GRAPH_SCHEMA,
        "graph_id": str(value.get("graph_id") or "client_previous"),
        "nodes": nodes,
        "edges": edges,
    }


def _add_node(
    nodes: dict[str, dict],
    *,
    node_id: str,
    kind: str,
    label: str,
    state: str,
    origin: str,
    turn: int | None = None,
    metadata: dict | None = None,
) -> None:
    if state not in CLAIM_STATES:
        raise ValueError(f"Unsupported task state: {state}")
    nodes[node_id] = {
        "id": node_id,
        "kind": kind,
        "label": label,
        "state": state,
        "origin": origin,
        "turn": turn,
        "metadata": metadata or {},
    }


def _add_edge(edges: dict[str, dict], source: str, target: str, relation: str) -> None:
    edge_id = _node_id("edge", f"{source}:{relation}:{target}")
    edges[edge_id] = {"id": edge_id, "source": source, "target": target, "relation": relation}


def _node_id(kind: str, value: str) -> str:
    return f"{kind}_{_sha(value)[:16]}"


def _graph_id(nodes: list[dict], edges: list[dict]) -> str:
    stable = {
        "nodes": [_stable_node(node) for node in nodes],
        "edges": edges,
    }
    return "graph_" + _sha(json.dumps(stable, ensure_ascii=False, sort_keys=True))[:20]


def _stable_node(node: dict) -> dict:
    return {key: value for key, value in node.items() if key not in {"built_at", "packet_id"}}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clip(value: str, limit: int) -> str:
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1] + "…"
