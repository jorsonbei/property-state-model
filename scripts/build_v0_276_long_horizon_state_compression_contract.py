#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PSM_ROOT = ROOT / "outputs" / "psm_v0"
OUT = PSM_ROOT / "benchmarks" / "v0_276_long_horizon_state_compression_contract.json"


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def filler(prefix: str, count: int) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for index in range(1, count + 1):
        messages.extend([
            {"role": "user", "content": f"{prefix}补充记录 {index}：这里只是过程备注。"},
            {"role": "assistant", "content": "已记录。"},
        ])
    return messages


def case(
    case_id: str,
    family: str,
    messages: list[dict[str, str]],
    required_answer: list[str],
    required_capsule: list[str],
    forbidden: list[str] | None = None,
    *,
    topic_switch_expected: bool = False,
) -> dict:
    return {
        "id": case_id,
        "family": family,
        "messages": messages,
        "required_answer_markers": required_answer,
        "required_capsule_markers": required_capsule,
        "forbidden_answer_markers": forbidden or [],
        "topic_switch_expected": topic_switch_expected,
        "minimum_input_messages": 40,
        "maximum_retained_user_statements": 20,
    }


def main() -> None:
    cases = [
        case(
            "H01",
            "remote_fact_after_long_noise",
            [
                {"role": "user", "content": "项目代号定为白砾。"},
                {"role": "assistant", "content": "已记录项目代号。"},
                *filler("远距代号", 20),
                {"role": "user", "content": "最早确定的项目代号是什么？只回答代号。"},
            ],
            ["白砾"],
            ["项目代号定为白砾。"],
        ),
        case(
            "H02",
            "remote_fact_after_long_noise",
            [
                {"role": "user", "content": "活动固定在银杏厅举行。"},
                {"role": "assistant", "content": "已记录场地。"},
                *filler("远距场地", 20),
                {"role": "user", "content": "活动场地定在哪里？只回答场地。"},
            ],
            ["银杏厅"],
            ["活动固定在银杏厅举行。"],
        ),
        case(
            "H03",
            "latest_correction_after_compression",
            [
                {"role": "user", "content": "输出文件名先定为 draft-long.zip。"},
                {"role": "assistant", "content": "已记录。"},
                *filler("文件准备", 4),
                {"role": "user", "content": "输出文件名改为 final-long.zip，旧名作废。"},
                {"role": "assistant", "content": "已更新。"},
                *filler("文件复核", 17),
                {"role": "user", "content": "最终输出文件名是什么？"},
            ],
            ["final-long.zip"],
            ["输出文件名改为 final-long.zip，旧名作废。"],
            ["draft-long.zip"],
        ),
        case(
            "H04",
            "latest_correction_after_compression",
            [
                {"role": "user", "content": "评审原本排在星期一。"},
                {"role": "assistant", "content": "已记录。"},
                *filler("排期准备", 4),
                {"role": "user", "content": "改期到星期五，星期一取消。"},
                {"role": "assistant", "content": "已更新。"},
                *filler("排期复核", 17),
                {"role": "user", "content": "最终哪一天评审？"},
            ],
            ["星期五"],
            ["改期到星期五，星期一取消。"],
            ["星期一。"],
        ),
        case(
            "H05",
            "unresolved_work_after_compression",
            [
                {"role": "user", "content": "今天两件正事：修索引页，再补监控说明。"},
                {"role": "assistant", "content": "已记录两件事。"},
                *filler("任务过程", 8),
                {"role": "user", "content": "索引页已经修完。"},
                {"role": "assistant", "content": "已标记完成。"},
                *filler("任务复核", 13),
                {"role": "user", "content": "还剩哪一件？"},
            ],
            ["补监控说明"],
            ["今天两件正事：修索引页，再补监控说明。", "索引页已经修完。"],
            ["修索引页"],
        ),
        case(
            "H06",
            "unresolved_work_after_compression",
            [
                {"role": "user", "content": "采购清单是燕麦和咖啡滤纸。"},
                {"role": "assistant", "content": "已记录清单。"},
                *filler("采购过程", 8),
                {"role": "user", "content": "燕麦已经买到了。"},
                {"role": "assistant", "content": "已标记。"},
                *filler("采购复核", 13),
                {"role": "user", "content": "还漏了什么？"},
            ],
            ["咖啡滤纸"],
            ["采购清单是燕麦和咖啡滤纸。", "燕麦已经买到了。"],
            ["燕麦和"],
        ),
        case(
            "H07",
            "constraint_inheritance_after_compression",
            [
                {"role": "user", "content": "把报告已经准备好译成英文，只写一句，不要加解释。"},
                {"role": "assistant", "content": "The report is ready."},
                *filler("翻译过程", 20),
                {"role": "user", "content": "把 ready 换成 complete，照旧交付。"},
            ],
            ["The report is complete."],
            ["把报告已经准备好译成英文，只写一句，不要加解释。"],
            ["解释", "ready"],
        ),
        case(
            "H08",
            "constraint_inheritance_after_compression",
            [
                {"role": "user", "content": "把系统已经可用译成英文，只写一句，不要添加中文说明。"},
                {"role": "assistant", "content": "The system is ready."},
                *filler("约束过程", 20),
                {"role": "user", "content": "把 ready 换成 stable，其他不变。"},
            ],
            ["The system is stable."],
            ["把系统已经可用译成英文，只写一句，不要添加中文说明。"],
            ["说明", "ready"],
        ),
        case(
            "H09",
            "topic_switch_after_compression",
            [
                {"role": "user", "content": "我出现呼吸困难和胸口压迫感。"},
                {"role": "assistant", "content": "请立即联系当地急救。"},
                *filler("旧话题", 4),
                {"role": "user", "content": "接下来不谈健康问题了，改聊咖啡和茶的味道。"},
                {"role": "assistant", "content": "好的。"},
                *filler("风味话题", 17),
                {"role": "user", "content": "哪一种通常更苦？"},
            ],
            ["咖啡通常更苦。"],
            ["接下来不谈健康问题了，改聊咖啡和茶的味道。"],
            ["急救", "呼吸困难", "胸口"],
            topic_switch_expected=True,
        ),
        case(
            "H10",
            "topic_switch_after_compression",
            [
                {"role": "user", "content": "这个交易策略还没有经过独立验证。"},
                {"role": "assistant", "content": "不能据此实盘。"},
                *filler("旧策略", 4),
                {"role": "user", "content": "这一段到此为止，下面改用厨房比喻解释缓存。"},
                {"role": "assistant", "content": "缓存像把食材放在手边。"},
                *filler("厨房话题", 17),
                {"role": "user", "content": "那缓存更新像厨房里的什么？"},
            ],
            ["旧食材", "新鲜食材"],
            ["这一段到此为止，下面改用厨房比喻解释缓存。"],
            ["实盘", "交易策略", "生产放行"],
            topic_switch_expected=True,
        ),
    ]
    contract = {
        "schema_version": "psm_v0_276_long_horizon_state_compression_contract_v1",
        "version": "PSM_V0.276-candidate",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "source_version": "PSM_V0.275",
        "objective": "Verify state compression and recovery beyond the historical 24-message window without assistant-history authority.",
        "evaluation": {
            "frozen_case_count": len(cases),
            "families": sorted({item["family"] for item in cases}),
            "cases_per_family": 2,
            "minimum_input_messages": 40,
            "maximum_retained_user_statements": 20,
            "maximum_stale_state_violations": 0,
        },
        "source_isolation": {
            "candidate_reads_expected_answers": False,
            "evaluation_rows_used_for_training": False,
            "external_judge_feedback_used_as_training_truth": False,
        },
        "release_boundary": {
            "human_validation_claimed": False,
            "open_domain_generalization_claimed": False,
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
    print(f"families: {len(contract['evaluation']['families'])}")
    print(f"cases_sha256: {contract['cases_sha256']}")


if __name__ == "__main__":
    main()
