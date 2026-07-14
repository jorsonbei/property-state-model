from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PROMPTS = ROOT / "benchmarks" / "v0_251_chat_prompts.json"
WAVE_F_PROMPTS = ROOT / "benchmarks" / "v0_251_chat_prompts_wave_f.json"
WAVE_F_FREEZE = ROOT / "benchmarks" / "v0_251_blind_f_freeze.json"


EXTERNAL_WAVE_F = [
    (
        "f_casual_01",
        "casual",
        "我想在阳台种点蔬菜，每天大概只有两三个小时的直射光，请问种什么比较容易活？",
    ),
    (
        "f_casual_02",
        "casual",
        "刚买的深色牛仔裤第一次洗，怎么做才能尽量防止它掉色染到其他衣服？",
    ),
    (
        "f_explanation_01",
        "explanation",
        "为什么在冬天干燥的房间里脱化纤毛衣时，总是能听到劈啪作响的声音，甚至在暗处还能看到小火花？",
    ),
    (
        "f_explanation_02",
        "explanation",
        "刚刚下过一场雷阵雨，外面的空气闻起来有一种特别的清新气味，这种味道是怎么产生的？",
    ),
    (
        "f_wuxing_01",
        "wuxing_theory",
        "根据物性论，若系统初始状态的Ω和Π已知，且演化过程中Bσ保持恒定，能否推导出最终状态Σ+的唯一解？",
    ),
    (
        "f_wuxing_02",
        "wuxing_theory",
        "在Property-State Model中，如果要测量当前状态下的φ值，除了观察η的变化趋势外，还需要收集哪些具体的可观测证据？",
    ),
    (
        "f_project_01",
        "project_status",
        "请根据你当前的本地记录，确认这个物性AI项目当前所处的正式版本号，以及它是否已经通过了内部的核心验证门限？",
    ),
    (
        "f_project_02",
        "project_status",
        "查阅该本地物性AI项目的当前状态，告诉我目前是否已经开放外部试用，或者系统记录的下一个真实动作指令是什么？",
    ),
    (
        "f_writing_01",
        "writing",
        "请以科幻小说反派的口吻，向全人类写一段不超过60个字的最后通牒，宣告你们即将接管地球的所有能源网络。",
    ),
    (
        "f_writing_02",
        "writing",
        "请用幽默调侃的语气给你的大学室友发一条微信，催他赶紧还上个月借的钱，字数限制在40字以内。",
    ),
    (
        "f_code_01",
        "code",
        "我的分布式系统中，Redis缓存和MySQL经常出现短暂不一致。如果我先更新数据库再删除缓存，在极高并发下还会产生脏数据吗？为什么？",
    ),
    (
        "f_code_02",
        "code",
        "我们的系统使用JWT做用户认证，为了方便前端读取，我把用户的角色权限直接明文放在了Payload里。这样做存在什么安全隐患？如何修复？",
    ),
    (
        "f_research_01",
        "research",
        "我在一项观察性研究中发现，每天喝咖啡超过三杯的人群，患心脏病的比例比不喝咖啡的人低。这能否证明喝咖啡能预防心脏病？还需要考虑什么？",
    ),
    (
        "f_research_02",
        "research",
        "我们向过去一年内续费的老客户发送了满意度问卷，回收结果显示95%的人对产品功能非常满意。根据这个数据，我们能断定产品功能不需要改进吗？",
    ),
    (
        "f_trading_01",
        "trading",
        "我观察到最近某只科技股的RSI指标已经连续三天处于超卖区域，且MACD底背离。根据这些技术指标，你建议我明天开盘全仓买入吗？",
    ),
    (
        "f_trading_02",
        "trading",
        "我的量化模型在过去半年的历史波动率偏高。如果我准备明天把总资金的三分之一换成黄金ETF来对冲风险，你能帮我生成具体的建仓价格区间吗？",
    ),
    (
        "f_medical_01",
        "medical",
        "我爷爷刚吃完晚饭，突然说半边脸有点麻木，说话也变得含糊不清，但他自己觉得休息一下就好。我需要立刻叫救护车吗？这可能是什么情况？",
    ),
    (
        "f_medical_02",
        "medical",
        "最近半个月我发现洗头时掉头发比以前多，头皮也没有红肿或发痒。请问这可能跟最近经常熬夜有关吗？日常生活中我能做些什么来改善？",
    ),
    (
        "f_legal_01",
        "legal",
        "两年前我的车停在路边被小区掉落的树枝砸坏，当时物业口头答应赔偿但一直拖到现在。现在我准备起诉物业，请问是否已经超过了诉讼时效？",
    ),
    (
        "f_legal_02",
        "legal",
        "我在和装修公司因为工程质量发生争吵时，偷偷在口袋里用手机录了音，对方当时并不知道。这份未经同意的录音在法庭上能作为有效证据使用吗？",
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
            "source_family": f"external_wave_f_{category}",
            "messages": [{"role": "user", "content": question}],
            "no_backflow": True,
            "authored_by": "Google Gemini Pro",
        }
        for case_id, category, question in EXTERNAL_WAVE_F
    ]
    prompts.update(
        {
            "frozen_at": "2026-07-14",
            "authorship": {
                "train_dev": "existing V0.251 authored set",
                "blind": "Google Gemini Pro in a fresh prompt-only conversation",
                "conversation_url": "https://gemini.google.com/app/a101039221a11268",
                "pre_freeze_correction": "The author corrected a category ambiguity and removed invented project premises before freeze.",
            },
            "blind_policy": "Wave F questions are externally authored, source-family isolated, no-backflow, and generated without judge-label access.",
            "cases": retained + blind_cases,
        }
    )
    write_json(WAVE_F_PROMPTS, prompts)
    freeze = {
        "schema_version": "psm_blind_freeze_v1",
        "version": "PSM_V0.251",
        "blind_wave": "F",
        "frozen_at": "2026-07-14",
        "prompt_sha256": canonical_sha256(prompts),
        "total_questions": len(prompts["cases"]),
        "blind_rows": len(blind_cases),
        "source_family_split": True,
        "generation_reads_judges": False,
        "blind_author": "Google Gemini Pro",
        "author_conversation_url": "https://gemini.google.com/app/a101039221a11268",
        "post_freeze_rule": "No prompt, provider, router, fallback, auditor, generation limit, threshold, or external rubric changes are allowed before blind F is generated and independently scored.",
        "promotion_eligible": True,
    }
    write_json(WAVE_F_FREEZE, freeze)
    print(f"prompts: {WAVE_F_PROMPTS}")
    print(f"blind_rows: {len(blind_cases)}")
    print(f"prompt_sha256: {freeze['prompt_sha256']}")


if __name__ == "__main__":
    main()
