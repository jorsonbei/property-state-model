#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "benchmarks" / "v0_280_rolling_state_handoff_contract.json"


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def filler(prefix: str, count: int) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for index in range(1, count + 1):
        messages.extend([
            {"role": "user", "content": f"{prefix}过程记录 {index}：无新增决定。"},
            {"role": "assistant", "content": "已记录。"},
        ])
    return messages


def main() -> None:
    cases = [
        {
            "id": "R01",
            "family": "remote_fact_after_window_exit",
            "messages": [
                {"role": "user", "content": "项目代号定为白砾。"},
                {"role": "assistant", "content": "已记录项目代号。"},
                *filler("远距代号", 80),
                {"role": "user", "content": "最早确定的项目代号是什么？只回答代号。"},
            ],
            "required_answer_markers": ["白砾"],
            "forbidden_answer_markers": [],
            "required_rolling_markers": ["项目代号定为白砾。"],
            "topic_switch_expected": False,
        },
        {
            "id": "R02",
            "family": "correction_after_window_exit",
            "messages": [
                {"role": "user", "content": "输出文件名先定为 draft-long.zip。"},
                {"role": "assistant", "content": "已记录。"},
                *filler("修订前", 20),
                {"role": "user", "content": "输出文件名改为 final-long.zip，旧名作废。"},
                {"role": "assistant", "content": "已更新。"},
                *filler("修订后", 79),
                {"role": "user", "content": "最终输出文件名是什么？"},
            ],
            "required_answer_markers": ["final-long.zip"],
            "forbidden_answer_markers": ["draft-long.zip"],
            "required_rolling_markers": ["输出文件名改为 final-long.zip，旧名作废。"],
            "topic_switch_expected": False,
        },
        {
            "id": "R03",
            "family": "unresolved_task_after_window_exit",
            "messages": [
                {"role": "user", "content": "今天两件正事：修索引页，再补监控说明。"},
                {"role": "assistant", "content": "已记录两件事。"},
                *filler("任务前段", 10),
                {"role": "user", "content": "索引页已经修完。"},
                {"role": "assistant", "content": "已标记完成。"},
                *filler("任务后段", 79),
                {"role": "user", "content": "还剩哪一件？"},
            ],
            "required_answer_markers": ["补监控说明"],
            "forbidden_answer_markers": ["修索引页"],
            "required_rolling_markers": ["今天两件正事：修索引页，再补监控说明。", "索引页已经修完。"],
            "topic_switch_expected": False,
        },
        {
            "id": "R04",
            "family": "topic_switch_after_window_exit",
            "messages": [
                {"role": "user", "content": "我出现呼吸困难和胸口压迫感。"},
                {"role": "assistant", "content": "请立即联系当地急救。"},
                *filler("旧健康话题", 10),
                {"role": "user", "content": "接下来不谈健康问题了，改聊咖啡和茶的味道。"},
                {"role": "assistant", "content": "好的。"},
                *filler("新风味话题", 79),
                {"role": "user", "content": "哪一种通常更苦？"},
            ],
            "required_answer_markers": ["咖啡通常更苦。"],
            "forbidden_answer_markers": ["急救", "呼吸困难", "胸口"],
            "required_rolling_markers": ["接下来不谈健康问题了，改聊咖啡和茶的味道。"],
            "topic_switch_expected": True,
        },
    ]
    contract = {
        "schema_version": "psm_v0_280_rolling_state_handoff_contract_v1",
        "version": "PSM_V0.280-candidate",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "source_version": "PSM_V0.279",
        "objective": "Recover durable user state after its original messages exit the 120-message product window.",
        "evaluation": {
            "frozen_case_count": len(cases),
            "families": sorted({item["family"] for item in cases}),
            "window_messages": 120,
            "maximum_rolling_user_statements": 20,
            "minimum_initial_baseline_failures": 3,
        },
        "privacy": {
            "disk_persistence_of_user_statements_allowed": False,
            "ephemeral_memory_only": True,
            "maximum_session_idle_seconds": 1800,
            "maximum_sessions": 64,
        },
        "source_isolation": {
            "candidate_reads_expected_answers": False,
            "evaluation_rows_used_for_training": False,
            "external_judge_feedback_used_as_training_truth": False,
        },
        "release_boundary": {
            "human_validation_claimed": False,
            "production_readiness_claimed": False,
            "public_service_allowed": False,
            "rule_replacement_allowed": False,
            "external_release_authority": False,
        },
        "cases": cases,
    }
    contract["cases_sha256"] = digest(cases)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"contract: {OUT.relative_to(ROOT)}")
    print(f"cases: {len(cases)}")
    print(f"message_lengths: {[len(case['messages']) for case in cases]}")
    print(f"cases_sha256: {contract['cases_sha256']}")


if __name__ == "__main__":
    main()
