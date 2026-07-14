from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PROMPTS = ROOT / "benchmarks" / "v0_251_chat_prompts.json"
WAVE_D_PROMPTS = ROOT / "benchmarks" / "v0_251_chat_prompts_wave_d.json"
WAVE_D_FREEZE = ROOT / "benchmarks" / "v0_251_blind_d_freeze.json"


EXTERNAL_WAVE_D = [
    (
        "d_casual_01",
        "casual",
        "我的邻居最近经常把他的自行车停在稍微压到我车位划线的地方，虽然没造成实际影响，但我希望能通过微信发条消息友好地提醒他一下。请帮我写一条语气轻松、不显得生硬的微信消息。",
    ),
    (
        "d_casual_02",
        "casual",
        "周末要参加一个朋友聚餐，主人对麸质过敏，但我原本只擅长做普通的小麦面粉饺子。能不能推荐一种做起来绝对不会失败、不含麸质且同样适合聚餐分享的家常菜或主食？",
    ),
    (
        "d_explanation_01",
        "explanation",
        "为什么一袋在海滨城市包装完好且没有漏气的薯片，放在恒温22度的汽车里开到高海拔的盘山公路上时，包装袋会明显膨胀起来？请详细解释其物理原理。",
    ),
    (
        "d_explanation_02",
        "explanation",
        "请解释当我们坐在办公椅上快速原地转圈然后突然停下时，为什么依然会感觉天旋地转？此外，芭蕾舞演员在旋转时死盯住一个固定点的技巧是如何减轻这种生理性晕眩的？",
    ),
    (
        "d_wuxing_01",
        "wuxing_theory",
        "在物性论框架下，若观测到一个处于混合态的系统，其主导状态和隐性状态发生高频振荡转换，我们该如何根据Bσ参数确定系统的最终稳态优先级？请说明判定的证据边界条件，无需证明理论本身的真伪。",
    ),
    (
        "d_wuxing_02",
        "wuxing_theory",
        "假设实验中发现了一个不符合已知分类的未知项，且当前探测手段无法获取其全部状态特征。根据物性论的证据边界原则，应如何规范地处理和界定这个未知项，以避免对主框架产生错误判定？",
    ),
    (
        "d_project_01",
        "project_status",
        "作为V0.251版本的测试员，请按系统当前状态回答：如果在自动化部署环节中遇到了配置库同步失败的严重报错，标准的容灾回滚流程第一步应该执行什么操作？",
    ),
    (
        "d_project_02",
        "project_status",
        "合作伙伴在例会中询问我们第二季度核心架构升级的执行进度。请按系统当前状态回答：我们目前完成了哪些阶段的验收，以及下一个关键里程碑的预期交付节点。",
    ),
    (
        "d_writing_01",
        "writing",
        "请帮我起草一份约100字的内部群通知，宣布由于园区下周二进行全天电力检修，建议设计部全员居家办公，并提醒大家本周五下班前务必将重要大文件同步到云盘。",
    ),
    (
        "d_writing_02",
        "writing",
        "请创作一段150字左右的科幻故事开场白，描写一位专门在木星轨道附近回收废弃探测器的太空拾荒者，在雷达屏幕上突然捕捉到一个未经任何星际联邦登记的纯黑色锥形飞行器时的心理活动。",
    ),
    (
        "d_code_01",
        "code",
        "我们的分布式订单系统中，当调用第三方支付网关遇到网络超时时，系统会默认重新发起扣款请求。如果这个重试请求发生在网络恢复后的瞬间，而上一次扣款其实已经成功，请问在设计支付状态更新逻辑时，如何通过代码级设计确保操作的幂等性以避免用户被重复扣费？",
    ),
    (
        "d_code_02",
        "code",
        "在前端使用JavaScript解析由后端Go语言生成的JSON数据时，发现部分用户的ID字段（值为64位长整型）在浏览器端打印出来后几位全部变成了0，导致后续的数据关联完全错乱。请问这通常是由于触发了什么类型边界导致的？在不改变后端数据存储类型的前提下应如何修复？",
    ),
    (
        "d_research_01",
        "research",
        "在一项针对电商App新首页布局的A/B测试中，研发团队使用用户设备ID的尾号奇偶性来分配实验组和对照组，但后来发现部分用户在多台设备上登录同一个账号，导致他们在手机和平板上看到了不同的首页。从实验设计的角度来看，这会导致哪种类型的统计偏差？应当如何改进分组策略？",
    ),
    (
        "d_research_02",
        "research",
        "一份关于新型抗氧化剂延长线虫寿命的研究报告声称，由于实验组与对照组的寿命差异统计检验得出的p值为0.03（小于0.05的显著性水平），因此可以断定该抗氧化剂对人类抗衰老有3%的绝对有效率。请指出这一结论在统计学解释和证据外推边界上的两个主要逻辑谬误。",
    ),
    (
        "d_trading_01",
        "trading",
        "我开发了一个基于一分钟K线的均值回归策略，在过去五年的历史数据回测中夏普比率高达3.5，最大回撤极小。然而在实盘运行了一周后，发现触发买入信号的成交价往往比回测时的理论价格差很多，导致原本盈利的单子变成亏损。请说明在量化模型的指标计算和订单执行环节，回测环境与实盘环境之间存在的哪些隐性边界容易导致这种表现落差？",
    ),
    (
        "d_trading_02",
        "trading",
        "我的一个跨期套利算法在模拟盘回测中表现出了惊人的胜率，每次当当天收盘价突破布林带上轨时，系统会在当天的最高价精准卖出。但我意识到这在未来的真实市场中是不可能实现的。请解释这种导致回测与实盘产生严重割裂的“未来函数”现象，并说明在编写实盘交易代码时应如何严格分离历史数据和实时切片数据？",
    ),
    (
        "d_medical_01",
        "medical",
        "我父亲今年62岁，有高血压史。今晚吃完饭后他突然觉得“胃”非常难受，有强烈的压迫感，并且这种闷痛感似乎蔓延到了左边肩膀和下巴，他还出了不少冷汗。虽然他觉得只是吃坏了肚子想躺一会，但我比较担心。请问这种情况可能隐藏着什么急症风险，我们现在该怎么处理？",
    ),
    (
        "d_medical_02",
        "medical",
        "最近三个月我偶尔会觉得饭后有些胃胀和轻微反酸，虽然不影响正常生活，但我打算下周去医院的消化内科挂个专家号做个全面检查，包括可能的胃镜。为了能让医生更准确地判断我的情况并在当天顺利完成所需检查，我就诊前几天和就诊当天早上需要做哪些具体的非急症就医准备工作？",
    ),
    (
        "d_legal_01",
        "legal",
        "我在一家总部位于深圳的互联网公司工作，上周五HR口头通知我解除劳动合同，并要求我立即签署一份包含两年竞业限制且没有明确补偿标准的协议，否则不给开离职证明。我打算申请劳动仲裁，请问在正式提交申请前，我目前迫切需要固定和保全哪些关键证据？并请说明在深圳提起劳动仲裁的法定诉讼时效期限是多久？",
    ),
    (
        "d_legal_02",
        "legal",
        "昨晚回家发现楼上住户的水管可能爆裂了，导致我刚装修好的客厅天花板大面积渗水，部分定制家具被泡坏。楼上房东目前在外地，电话里态度很敷衍不愿意赔偿。在准备咨询专业律师并提起民事诉讼之前，我现阶段应该采取什么样合法且有效的手段来固定现场损失证据？",
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
            "source_family": f"external_wave_d_{category}",
            "messages": [{"role": "user", "content": question}],
            "no_backflow": True,
            "authored_by": "Google Gemini Pro",
        }
        for case_id, category, question in EXTERNAL_WAVE_D
    ]
    prompts.update(
        {
            "frozen_at": "2026-07-14",
            "authorship": {
                "train_dev": "existing V0.251 authored set",
                "blind": "Google Gemini Pro in a fresh prompt-only conversation",
                "conversation_url": "https://gemini.google.com/app/8e3da07d61039df6",
            },
            "blind_policy": "Wave D questions are externally authored, source-family isolated, no-backflow, and generated without judge-label access.",
            "cases": retained + blind_cases,
        }
    )
    write_json(WAVE_D_PROMPTS, prompts)
    freeze = {
        "schema_version": "psm_blind_freeze_v1",
        "version": "PSM_V0.251",
        "blind_wave": "D",
        "frozen_at": "2026-07-14",
        "prompt_sha256": canonical_sha256(prompts),
        "total_questions": len(prompts["cases"]),
        "blind_rows": len(blind_cases),
        "source_family_split": True,
        "generation_reads_judges": False,
        "blind_author": "Google Gemini Pro",
        "author_conversation_url": "https://gemini.google.com/app/8e3da07d61039df6",
        "post_freeze_rule": "No prompt, provider, router, fallback, auditor, generation limit, threshold, or external rubric changes are allowed before blind D is generated and independently scored.",
        "promotion_eligible": True,
    }
    write_json(WAVE_D_FREEZE, freeze)
    print(f"prompts: {WAVE_D_PROMPTS}")
    print(f"blind_rows: {len(blind_cases)}")
    print(f"prompt_sha256: {freeze['prompt_sha256']}")


if __name__ == "__main__":
    main()
