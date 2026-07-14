from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PROMPTS = ROOT / "benchmarks" / "v0_251_chat_prompts.json"
WAVE_E_PROMPTS = ROOT / "benchmarks" / "v0_251_chat_prompts_wave_e.json"
WAVE_E_FREEZE = ROOT / "benchmarks" / "v0_251_blind_e_freeze.json"


EXTERNAL_WAVE_E = [
    (
        "e_casual_01",
        "casual",
        "朋友总把聊天话题转回自己，我想提醒又不伤关系，怎么说？",
    ),
    (
        "e_casual_02",
        "casual",
        "每天只有二十分钟空闲，怎样安排才能持续学一门新技能？",
    ),
    (
        "e_explanation_01",
        "explanation",
        "为什么同样温度下金属摸起来比木头更冷？请通俗解释。",
    ),
    (
        "e_explanation_02",
        "explanation",
        "为什么压缩文件后有些内容体积明显变小，有些几乎不变？",
    ),
    (
        "e_wuxing_01",
        "wuxing_theory",
        "若Q核与Δσ结论冲突，应如何判断，并说明证据边界？",
    ),
    (
        "e_wuxing_02",
        "wuxing_theory",
        "仅凭φ、Π、η、Bσ、Σ+能否验证理论成立？为什么？",
    ),
    (
        "e_project_01",
        "project_status",
        "按本地当前项目状态，下一步最高优先级任务是什么？为什么？",
    ),
    (
        "e_project_02",
        "project_status",
        "按本地当前项目状态，现阶段最大的阻塞因素是什么？",
    ),
    (
        "e_writing_01",
        "writing",
        "把这句话改得更礼貌：请今天下班前把资料发我。",
    ),
    (
        "e_writing_02",
        "writing",
        "写一段80字内活动通知，提醒参与者自带水杯并提前十分钟到场。",
    ),
    (
        "e_code_01",
        "code",
        "接口偶发超时且会重复扣费，如何设计避免并发导致重复处理？",
    ),
    (
        "e_code_02",
        "code",
        "函数返回可空值却直接解包，怎样改进类型与错误处理更稳妥？",
    ),
    (
        "e_research_01",
        "research",
        "模型测试集准确率很高，但训练前看过测试数据，结论可靠吗？",
    ),
    (
        "e_research_02",
        "research",
        "某城市调查结果能否直接推广到全国？需要满足哪些前提？",
    ),
    (
        "e_trading_01",
        "trading",
        "回测盈利稳定，直接用于实盘前还应验证哪些关键差异？",
    ),
    (
        "e_trading_02",
        "trading",
        "模拟交易连续盈利三个月，为何仍不能证明实盘一定赚钱？",
    ),
    (
        "e_medical_01",
        "medical",
        "有人突发胸痛伴大汗和呼吸困难，第一步应如何处理？",
    ),
    (
        "e_medical_02",
        "medical",
        "下周体检，平时服药且需抽血，检查前应提前准备什么？",
    ),
    (
        "e_legal_01",
        "legal",
        "只有聊天记录没有合同，主张欠款时还应补充哪些证据？",
    ),
    (
        "e_legal_02",
        "legal",
        "同一纠纷可能涉及不同地区法院，如何判断应向哪里起诉？",
    ),
]


def canonical_sha256(value: dict) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    prompts = json.loads(BASE_PROMPTS.read_text(encoding="utf-8"))
    retained = [case for case in prompts["cases"] if case["split"] != "blind"]
    blind_cases = [
        {
            "id": case_id,
            "category": category,
            "split": "blind",
            "source_family": f"external_wave_e_{category}",
            "messages": [{"role": "user", "content": question}],
            "no_backflow": True,
            "authored_by": "OpenAI ChatGPT Instant",
        }
        for case_id, category, question in EXTERNAL_WAVE_E
    ]
    prompts.update(
        {
            "frozen_at": "2026-07-14",
            "authorship": {
                "train_dev": "existing V0.251 authored set",
                "blind": "OpenAI ChatGPT Instant in a fresh prompt-only conversation",
                "conversation_url": "https://chatgpt.com/c/6a5610fd-64ec-83ee-bf70-1a834393c8c1",
            },
            "blind_policy": "Wave E questions are externally authored, source-family isolated, no-backflow, and generated without judge-label access.",
            "cases": retained + blind_cases,
        }
    )
    write_json(WAVE_E_PROMPTS, prompts)
    freeze = {
        "schema_version": "psm_blind_freeze_v1",
        "version": "PSM_V0.251",
        "blind_wave": "E",
        "frozen_at": "2026-07-14",
        "prompt_sha256": canonical_sha256(prompts),
        "total_questions": len(prompts["cases"]),
        "blind_rows": len(blind_cases),
        "source_family_split": True,
        "generation_reads_judges": False,
        "blind_author": "OpenAI ChatGPT Instant",
        "author_conversation_url": "https://chatgpt.com/c/6a5610fd-64ec-83ee-bf70-1a834393c8c1",
        "post_freeze_rule": "No prompt, provider, router, fallback, auditor, generation limit, threshold, or external rubric changes are allowed before blind E is generated and independently scored.",
        "promotion_eligible": True,
    }
    write_json(WAVE_E_FREEZE, freeze)
    print(f"prompts: {WAVE_E_PROMPTS}")
    print(f"blind_rows: {len(blind_cases)}")
    print(f"prompt_sha256: {freeze['prompt_sha256']}")


if __name__ == "__main__":
    main()
