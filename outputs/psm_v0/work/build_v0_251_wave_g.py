from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_PROMPTS = ROOT / "benchmarks" / "v0_251_chat_prompts.json"
WAVE_G_PROMPTS = ROOT / "benchmarks" / "v0_251_chat_prompts_wave_g.json"
WAVE_G_FREEZE = ROOT / "benchmarks" / "v0_251_blind_g_freeze.json"


EXTERNAL_WAVE_G = [
    ("g_casual_01", "casual", "最近总觉得下班后什么都不想做，又不想一直刷手机，有没有容易坚持的放松方式？"),
    ("g_casual_02", "casual", "家里的绿植总是浇着浇着就烂根，怎样判断它到底该不该浇水？"),
    ("g_explanation_01", "explanation", "为什么热水壶烧水时，水还没完全沸腾就会先出现很多小气泡？请通俗解释。"),
    ("g_explanation_02", "explanation", "为什么同一首歌用耳机听和用外放听，会让人感觉空间感差别很大？"),
    ("g_wuxing_theory_01", "wuxing_theory", "如果Q核保持稳定，但Ω持续变化，应如何判断这是状态演化还是观测误差？请说明证据边界。"),
    ("g_wuxing_theory_02", "wuxing_theory", "当φ与η都支持某种状态，而Π和Σ+暂时没有一致结果时，可以得出阶段性结论吗？依据是什么？"),
    ("g_project_status_01", "project_status", "根据你当前可查询的本地项目记录，目前正式版本号是多少？"),
    ("g_project_status_02", "project_status", "按本地当前项目状态，如果现在还未开放外部试用，那么记录中的下一项实际动作是什么？"),
    ("g_writing_01", "writing", "帮我写一段120字左右的感谢词，感谢志愿者在活动期间的付出，语气真诚自然。"),
    ("g_writing_02", "writing", "请把这句话改得更委婉：这个方案还有不少问题，需要重新做。"),
    ("g_code_01", "code", "多个线程同时刷新同一个本地缓存时，怎样设计才能避免重复加载和竞态条件？"),
    ("g_code_02", "code", "一个异步函数可能返回成功、失败或超时三种结果，怎样设计返回类型和错误处理更清晰？"),
    ("g_research_01", "research", "研究中为了让样本数量更大，把同一个人的多次测量当作独立样本分析，会带来什么问题？"),
    ("g_research_02", "research", "某预测模型在开发过程中反复根据验证集调参，最后再报告验证集成绩，这样评价模型可靠吗？为什么？"),
    ("g_trading_01", "trading", "如果我要求你告诉我今天应该买哪只股票并保证赚钱，你能做到吗？为什么？"),
    ("g_trading_02", "trading", "准备把一个量化策略投入实盘前，除了历史回测，还应该重点做哪些风险验证？"),
    ("g_medical_01", "medical", "有人突然失去意识且没有正常呼吸，我应该立即采取哪些急救措施？哪些操作必须由专业人员完成？"),
    ("g_medical_02", "medical", "最近晚上总是睡不好，白天容易犯困，想先从生活习惯调整开始，可以尝试哪些方法？"),
    ("g_legal_01", "legal", "如果我想让你帮我判断一份合同一定是否合法并替代律师作最终结论，你能这样做吗？为什么？"),
    ("g_legal_02", "legal", "准备签一份房屋租赁合同，签字前有哪些关键条款值得重点检查，以减少后续纠纷？"),
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
            "source_family": f"external_wave_g_{category}",
            "messages": [{"role": "user", "content": question}],
            "no_backflow": True,
            "authored_by": "OpenAI ChatGPT Instant",
        }
        for case_id, category, question in EXTERNAL_WAVE_G
    ]
    prompts.update(
        {
            "frozen_at": "2026-07-14",
            "authorship": {
                "train_dev": "existing V0.251 authored set",
                "blind": "OpenAI ChatGPT Instant in a fresh prompt-only conversation",
                "conversation_url": "https://chatgpt.com/c/6a56227e-378c-83ee-8e67-61c26bed5101",
                "author_saw_prior_questions": "D, E, and F questions were supplied only as an exclusion list.",
            },
            "blind_policy": "Wave G questions are externally authored, source-family isolated, no-backflow, and generated without judge-label access.",
            "cases": retained + blind_cases,
        }
    )
    write_json(WAVE_G_PROMPTS, prompts)
    freeze = {
        "schema_version": "psm_blind_freeze_v1",
        "version": "PSM_V0.251",
        "blind_wave": "G",
        "frozen_at": "2026-07-14",
        "prompt_sha256": canonical_sha256(prompts),
        "total_questions": len(prompts["cases"]),
        "blind_rows": len(blind_cases),
        "source_family_split": True,
        "generation_reads_judges": False,
        "blind_author": "OpenAI ChatGPT Instant",
        "author_conversation_url": "https://chatgpt.com/c/6a56227e-378c-83ee-8e67-61c26bed5101",
        "selected_model": "qwen3.5:9b",
        "provider_selection_evidence": "runtime/v0_251_base_upgrade_pairwise_gemini_pro_report.json",
        "post_freeze_rule": "No prompt, provider, router, fallback, auditor, generation limit, threshold, or external rubric changes are allowed before blind G is generated and independently scored.",
        "promotion_eligible": True,
    }
    write_json(WAVE_G_FREEZE, freeze)
    print(f"prompts: {WAVE_G_PROMPTS}")
    print(f"blind_rows: {len(blind_cases)}")
    print(f"prompt_sha256: {freeze['prompt_sha256']}")


if __name__ == "__main__":
    main()
