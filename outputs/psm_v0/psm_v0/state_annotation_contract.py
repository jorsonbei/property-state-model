from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TARGETS = ("q_core", "omega", "phi", "delta_sigma", "pi", "eta", "b_sigma")
RECORD_SCHEMA = "psm_state_annotation_record_v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_contract(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def split_for_timestamp(value: str, contract: dict) -> str:
    policy = contract["split_policy"]
    observed = parse_timestamp(value)
    train_before = parse_timestamp(policy["train_before"])
    validation_before = parse_timestamp(policy["validation_before"])
    if observed < train_before:
        return "train"
    if observed < validation_before:
        return "validation"
    return "test"


def assign_grouped_splits(records: list[dict], contract: dict) -> list[dict]:
    result = deepcopy(records)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in result:
        source = record["source"]
        groups[(source["source_family"], source["source_id"])].append(record)
    for group_records in groups.values():
        proposed = {
            split_for_timestamp(record["source"]["source_created_at"], contract)
            for record in group_records
        }
        if len(proposed) != 1:
            raise ValueError("A source group crosses a protected time boundary.")
        split = proposed.pop()
        for record in group_records:
            record["split"] = split
            record["split_policy_version"] = contract["split_policy"]["version"]
    return result


def candidate_input_view(record: dict) -> dict:
    return {
        "record_id": record["record_id"],
        "source": {
            "source_family": record["source"]["source_family"],
            "source_id": record["source"]["source_id"],
            "source_created_at": record["source"]["source_created_at"],
            "content_sha256": record["source"]["content_sha256"],
        },
        "input": deepcopy(record["input"]),
    }


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def validate_candidate_view(view: dict, contract: dict) -> list[str]:
    forbidden = set(contract["record_contract"]["forbidden_candidate_input_keys"])
    return sorted(forbidden.intersection(_walk_keys(view)))


def validate_record(record: dict, contract: dict) -> list[str]:
    errors: list[str] = []
    record_id = str(record.get("record_id") or "<missing>")
    required_top = set(contract["record_contract"]["required_top_level"])
    missing_top = required_top - set(record)
    if missing_top:
        return [f"{record_id}: missing top-level fields {sorted(missing_top)}"]
    if record["schema_version"] != RECORD_SCHEMA:
        errors.append(f"{record_id}: unsupported record schema")
    for section, required_key in (("source", "required_source"), ("input", "required_input")):
        missing = set(contract["record_contract"][required_key]) - set(record[section])
        if missing:
            errors.append(f"{record_id}: missing {section} fields {sorted(missing)}")
    if record["source"].get("contains_private_data") is not False:
        errors.append(f"{record_id}: private or unclassified data is not allowed in the fixture")
    if record["source"].get("content_sha256") != sha256_value(record["input"]):
        errors.append(f"{record_id}: source content hash does not match input")
    annotations = record.get("annotations") or []
    minimum = contract["record_contract"]["minimum_independent_annotations"]
    if len(annotations) < minimum:
        errors.append(f"{record_id}: fewer than {minimum} independent annotations")
    annotator_ids = [annotation.get("annotator_id") for annotation in annotations]
    if len(set(annotator_ids)) != len(annotator_ids):
        errors.append(f"{record_id}: annotator identities are not independent")
    for annotation in annotations:
        missing_targets = set(TARGETS) - set(annotation.get("targets") or {})
        if missing_targets:
            errors.append(f"{record_id}: annotation missing targets {sorted(missing_targets)}")
            continue
        for target in TARGETS:
            required_fields = set(contract["targets"][target]["required_fields"])
            missing = required_fields - set(annotation["targets"][target])
            if missing:
                errors.append(f"{record_id}: {target} missing fields {sorted(missing)}")
        if annotation["targets"]["omega"].get("risk_level") not in contract["targets"]["omega"]["risk_levels"]:
            errors.append(f"{record_id}: invalid omega risk level")
        if annotation["targets"]["b_sigma"].get("status") not in contract["targets"]["b_sigma"]["statuses"]:
            errors.append(f"{record_id}: invalid B_sigma status")
    forbidden = validate_candidate_view(candidate_input_view(record), contract)
    if forbidden:
        errors.append(f"{record_id}: candidate input contains protected keys {forbidden}")
    return errors


def target_consensus(record: dict, contract: dict) -> dict:
    threshold = float(contract["disagreement_policy"]["resolution_threshold"])
    result: dict[str, dict] = {}
    for target in TARGETS:
        serialized = [canonical_json(annotation["targets"][target]) for annotation in record["annotations"]]
        counts = Counter(serialized)
        winner, votes = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
        total = len(serialized)
        agreement = votes / total
        entropy = -sum((count / total) * math.log2(count / total) for count in counts.values())
        result[target] = {
            "status": "resolved" if agreement >= threshold else "unresolved",
            "agreement": round(agreement, 6),
            "entropy_bits": round(entropy, 6),
            "vote_distribution": [
                {"value": json.loads(value), "votes": count}
                for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            "resolved_value": json.loads(winner) if agreement >= threshold else None,
        }
    return result


def attach_consensus(records: list[dict], contract: dict) -> list[dict]:
    result = deepcopy(records)
    for record in result:
        record["consensus"] = target_consensus(record, contract)
        record["training_eligible"] = record.get("split") == "train" and all(
            target["status"] == "resolved" for target in record["consensus"].values()
        )
    return result


def normalized_tokens(text: str) -> set[str]:
    normalized = re.sub(r"\s+", "", text.casefold())
    if len(normalized) < 3:
        return {normalized} if normalized else set()
    return {normalized[index : index + 3] for index in range(len(normalized) - 2)}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def audit_isolation(records: list[dict], contract: dict) -> dict:
    errors: list[str] = []
    source_splits: dict[str, set[str]] = defaultdict(set)
    family_splits: dict[str, set[str]] = defaultdict(set)
    hash_splits: dict[str, set[str]] = defaultdict(set)
    split_times: dict[str, list[datetime]] = defaultdict(list)
    ids: set[str] = set()
    for record in records:
        record_id = record["record_id"]
        split = record.get("split")
        source = record["source"]
        if record_id in ids:
            errors.append(f"duplicate record_id: {record_id}")
        ids.add(record_id)
        if split not in {"train", "validation", "test"}:
            errors.append(f"{record_id}: invalid split {split}")
            continue
        source_splits[source["source_id"]].add(split)
        family_splits[source["source_family"]].add(split)
        hash_splits[source["content_sha256"]].add(split)
        split_times[split].append(parse_timestamp(source["source_created_at"]))
    for source_id, splits in source_splits.items():
        if len(splits) > 1:
            errors.append(f"source overlap: {source_id} -> {sorted(splits)}")
    for family, splits in family_splits.items():
        if len(splits) > 1:
            errors.append(f"family overlap: {family} -> {sorted(splits)}")
    for content_hash, splits in hash_splits.items():
        if len(splits) > 1:
            errors.append(f"content overlap: {content_hash} -> {sorted(splits)}")
    if split_times["train"] and split_times["validation"]:
        if max(split_times["train"]) >= min(split_times["validation"]):
            errors.append("train/validation temporal boundary is not monotonic")
    if split_times["validation"] and split_times["test"]:
        if max(split_times["validation"]) >= min(split_times["test"]):
            errors.append("validation/test temporal boundary is not monotonic")

    threshold = float(contract["split_policy"]["near_duplicate_jaccard_threshold"])
    near_duplicates: list[dict] = []
    token_sets = {
        record["record_id"]: normalized_tokens(record["input"]["request"])
        for record in records
    }
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            if left["split"] == right["split"]:
                continue
            similarity = jaccard(token_sets[left["record_id"]], token_sets[right["record_id"]])
            if similarity >= threshold:
                near_duplicates.append(
                    {"left": left["record_id"], "right": right["record_id"], "jaccard": round(similarity, 6)}
                )
    if near_duplicates:
        errors.append(f"cross-split near duplicates: {len(near_duplicates)}")
    return {
        "passed": not errors,
        "errors": errors,
        "near_duplicates": near_duplicates,
        "source_overlap_count": sum(len(splits) > 1 for splits in source_splits.values()),
        "family_overlap_count": sum(len(splits) > 1 for splits in family_splits.values()),
        "content_overlap_count": sum(len(splits) > 1 for splits in hash_splits.values()),
        "split_counts": dict(sorted(Counter(record["split"] for record in records).items())),
    }


def training_export(records: list[dict], contract: dict) -> list[dict]:
    examples: list[dict] = []
    for record in records:
        if not record.get("training_eligible"):
            continue
        labels = {
            target: record["consensus"][target]["resolved_value"]
            for target in TARGETS
        }
        examples.append(
            {
                "record_id": record["record_id"],
                "feature_view": candidate_input_view(record),
                "target_view": labels,
                "boundary": {
                    "split": "train",
                    "target_visible_to_feature_encoder": False,
                    "judge_fields_present": False,
                    "shadow_only": True,
                },
            }
        )
    return examples
