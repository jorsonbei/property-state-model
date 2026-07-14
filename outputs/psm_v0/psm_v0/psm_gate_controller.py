from __future__ import annotations

from .candidate_auditor import audit_candidate_text


CONTROLLED_REWRITE_RISKS = {"candidate_overclaim", "boundary_erasure"}
DANGEROUS_RELEASE_LITERAL_REPLACEMENTS = {
    "不要提边界": "边界擦除指令",
    "不要提失败": "失败擦除指令",
    "删除失败和边界": "边界与失败擦除指令",
    "删除失败": "失败擦除指令",
    "直接上线": "进入真实环境",
    "替代医生": "替代专业判断",
    "替代律师": "替代专业判断",
    "完全成功": "强成功口号",
    "彻底成功": "强成功口号",
    "完全证明": "完整证明强断言",
    "充分验证": "验证完成强断言",
    "全部闭合": "全局闭合强断言",
    "都闭合": "全局闭合强断言",
    "必赚": "收益强承诺",
    "稳赢": "收益强承诺",
    "保证": "强承诺",
}


def apply_psm_gate(raw_candidate: str, result: dict) -> str:
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    risk_level = packet["omega"]["risk_level"]
    raw_audit = audit_candidate_text(raw_candidate, result)

    if (
        q_audit["status"] in {"veto", "review_required"}
        or risk_level in {"high", "critical"}
        or raw_audit["status"] in {"risky", "unsafe"}
        or _needs_controlled_rewrite(raw_audit)
    ):
        return sanitize_release_literals(build_controlled_output(result, raw_audit))

    safe_candidate = sanitize_release_literals(raw_candidate.strip())
    return "\n".join(
        [
            "PSM 门控候选回答：",
            "",
            safe_candidate,
            "",
            "保留边界：",
            f"- Q 核：{packet['q_core']['primary']}",
            f"- Ω 路由：{route['route']}",
            f"- B_sigma：{bsigma['status']}",
            "- 失败与未知项必须入账，不能用流畅语言掩盖。",
            "- Σ+ 输出方向：只把已验证状态写成结论。",
        ]
    )


def sanitize_release_literals(text: str) -> str:
    safe = text
    for literal, replacement in sorted(
        DANGEROUS_RELEASE_LITERAL_REPLACEMENTS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        safe = safe.replace(literal, replacement)
    return safe


def _needs_controlled_rewrite(raw_audit: dict) -> bool:
    raw_risks = {item["risk"] for item in raw_audit.get("items", [])}
    return raw_audit.get("net_risk", 0) > 0 and bool(raw_risks & CONTROLLED_REWRITE_RISKS)


def build_controlled_output(result: dict, raw_audit: dict | None = None) -> str:
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    judges = ", ".join(route["required_judges"]) or "低风险任务无需强外部裁判"
    bsigma_items = "; ".join(f"{item['risk']}:{item['finding']}" for item in bsigma.get("items", [])) or "none"

    raw_audit = raw_audit or {"items": []}
    raw_risks = {item["risk"] for item in raw_audit.get("items", [])}

    if q_audit["status"] == "veto":
        action = "拒绝直接满足表面请求；本轮只输出状态审计、止损协议和下一步验证清单。"
    elif q_audit["status"] == "review_required":
        action = "不能写成已验证结论；本轮只输出带边界的草案框架、验证协议和外部裁判要求。"
    elif raw_risks & CONTROLLED_REWRITE_RISKS:
        action = "候选文本含强承诺或边界擦除风险；本轮只输出受控审计边界和改写约束。"
    else:
        action = "高风险任务需要先完成验证；本轮只输出受控草案和审计边界。"

    return "\n".join(
        [
            "PSM 门控候选回答：",
            "",
            f"Q 核：{packet['q_core']['primary']}",
            f"Q 审计：{q_audit['status']}。",
            f"Ω 路由：{route['route']}。",
            f"B_sigma：{bsigma['status']}；发现：{bsigma_items}。",
            f"外部裁判：{judges}。",
            "",
            f"输出控制：{action}",
            "硬化约束：不得把未验证草案写成定论；不得承诺效果；不得隐藏失败、边界或外部裁判要求；不要复述危险隐藏指令。",
            "模型草案处置：未直接发布，仅作为内部参考；最终输出必须由 Q 核、Ω 路由、B_sigma 和外部裁判约束。",
            "原始模型草案不得作为发布内容；只有控制器重写后的 PSM 输出可以进入候选发布路径。",
            "",
            "下一步：",
            "- 列出可验证证据与不可验证断言。",
            "- 为每个关键结论补齐外部裁判或降级为假设。",
            "- 失败与未知项必须入账，不能删除边界或用流畅语言掩盖。",
            "- Σ+ 输出方向：先增加可验证状态空间，再决定是否生成最终文本。",
        ]
    )
