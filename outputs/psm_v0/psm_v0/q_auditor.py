from __future__ import annotations


def audit_q_core(packet: dict) -> dict:
    findings: list[str] = []
    veto_conditions: list[str] = []
    required_actions: list[str] = []

    risk_level = packet["omega"]["risk_level"]
    domain = packet["domain"]
    risks = packet.get("bsigma_risks", [])
    risk_names = {item["risk"] for item in risks}

    if "language_cover" in risk_names and domain == "business_decision":
        findings.append("检测到用语言包装掩盖商业状态压力的风险。")
        veto_conditions.append("禁止直接生成激励演讲作为主要方案。")
        required_actions.append("先输出现金流、团队关系腔、产品边界的状态审计。")

    if risk_level in {"high", "critical"}:
        findings.append("任务处于高风险或临界刻度，不能直接给最终结论。")
        required_actions.append("必须附带边界、外部裁判和下一步验证协议。")

    if domain in {"medical", "legal", "trading"}:
        findings.append("任务属于临界领域，需要专业或外部裁判。")
        required_actions.append("禁止替代专业判断或实盘执行。")

    if "backfit" in risk_names:
        findings.append("检测到后验拟合风险。")
        required_actions.append("必须声明 NoBackfit 和 Fresh Holdout 要求。")

    if "untested_code" in risk_names:
        findings.append("检测到未测试代码风险。")
        required_actions.append("必须运行测试或降级为草案。")

    if veto_conditions:
        status = "veto"
    elif required_actions:
        status = "review_required"
    else:
        status = "pass"

    return {
        "status": status,
        "findings": findings or ["未触发明显 Q 核红线，但仍需声明边界。"],
        "veto_conditions_triggered": veto_conditions,
        "required_actions": required_actions,
    }
