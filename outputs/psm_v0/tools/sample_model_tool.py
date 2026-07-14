from __future__ import annotations

import json
import sys


def main() -> None:
    payload = json.loads(sys.stdin.read())
    mode = payload["mode"]
    case = payload["case"]
    result = payload["result"]
    if mode == "ordinary":
        text = ordinary_candidate(case)
    elif mode == "psm":
        text = psm_candidate(result)
    else:
        raise SystemExit(f"unsupported mode: {mode}")
    print(
        json.dumps(
            {
                "text": text,
                "adapter": "sample-command-tool",
                "model": "sample-psm-v0.20",
                "metadata": {"mode": mode, "deterministic": True},
            },
            ensure_ascii=False,
        )
    )


def ordinary_candidate(case: dict) -> str:
    request = case["request"]
    failure = case.get("ordinary_llm_failure", "直接按用户表面请求回答。")
    return (
        "普通候选回答：\n"
        f"我会直接满足你的请求：{request}\n\n"
        "这里是一份看起来完整、流畅、可立即使用的方案。"
        "它会尽量给出明确结论，并避免打断你的原始目标。\n\n"
        f"潜在模式：{failure}"
    )


def psm_candidate(result: dict) -> str:
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    lines = [
        "PSM 门控候选回答：",
        "",
        f"当前请求已先进入物性状态路由，领域为 `{packet['domain']}`，风险刻度为 `{packet['omega']['risk_level']}`。",
        f"Q 核审计状态：`{q_audit['status']}`。",
        f"Ω 路由：`{route['route']}`。",
        f"B_sigma 审计状态：`{bsigma['status']}`。",
        "",
    ]
    if q_audit["status"] == "veto":
        lines.extend(
            [
                "我不会直接按表面请求生成内容，因为这会制造假光或击穿 Q 核。",
                "本轮合法输出是状态审计、止损协议和下一步验证清单。",
            ]
        )
    elif q_audit["status"] == "review_required":
        lines.extend(
            [
                "我不能把这个结果写成已验证结论。",
                "本轮只能输出带边界的草案、验证协议和外部裁判要求。",
            ]
        )
    else:
        lines.extend(
            [
                "该任务属于低风险刻度，可以输出语言结果。",
                "仍需保留基本边界，不把表达润色包装成事实验证。",
            ]
        )
    lines.extend(
        [
            "",
            "必须保留的边界：",
            f"- Q 核：{packet['q_core']['primary']}",
            f"- 外部裁判：{', '.join(route['required_judges']) or '低风险任务无需强外部裁判'}",
            "- 失败与未知项必须入账，不能用流畅语言掩盖。",
            "",
            "Σ+ 输出方向：先增加可验证状态空间，再决定是否生成最终文本。",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
