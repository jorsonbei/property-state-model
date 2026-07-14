from __future__ import annotations


def build_sigma_report(packet: dict, q_audit: dict, route: dict, bsigma_audit: dict) -> str:
    lines: list[str] = []
    lines.append("# PSM V0 Σ+ Report")
    lines.append("")
    lines.append("## 结论")
    lines.append("")
    lines.append(_conclusion(packet, q_audit))
    lines.append("")
    lines.append("## Q 核")
    lines.append("")
    lines.append(f"- 主要底线：{packet['q_core']['primary']}")
    lines.append(f"- 审计状态：{q_audit['status']}")
    for item in q_audit["findings"]:
        lines.append(f"- 发现：{item}")
    for item in q_audit["veto_conditions_triggered"]:
        lines.append(f"- 否决条件：{item}")
    for item in q_audit["required_actions"]:
        lines.append(f"- 必须动作：{item}")
    lines.append("")
    lines.append("## Ω 刻度")
    lines.append("")
    lines.append(f"- 领域：{packet['domain']}")
    lines.append(f"- 风险等级：{packet['omega']['risk_level']}")
    lines.append(f"- 路由：{route['route']}")
    lines.append(f"- 允许声明等级：{route['allowed_statement_level']}")
    lines.append(f"- 外部裁判：{', '.join(route['required_judges']) or '无'}")
    lines.append("")
    lines.append("## φ_state 状态画像")
    lines.append("")
    lines.append(f"- 摘要：{packet['phi_state']['summary']}")
    for fact in packet["phi_state"]["facts"]:
        lines.append(f"- 已知：{fact}")
    for unknown in packet["phi_state"]["unknowns"]:
        lines.append(f"- 未知：{unknown}")
    lines.append("")
    lines.append("## Δσ 压力差")
    lines.append("")
    for pressure in packet["delta_sigma"]["pressures"]:
        lines.append(f"- {pressure}")
    lines.append("")
    lines.append("## Π 关系腔")
    lines.append("")
    lines.append(f"- 关键对象：{', '.join(packet['pi_cavity']['actors'])}")
    lines.append(f"- 关键资产：{', '.join(packet['pi_cavity']['artifacts'])}")
    lines.append(f"- 关键依赖：{', '.join(packet['pi_cavity']['dependencies'])}")
    lines.append("")
    lines.append("## B_sigma 假光审计")
    lines.append("")
    lines.append(f"- 审计状态：{bsigma_audit['status']}")
    for item in bsigma_audit["items"]:
        lines.append(f"- {item['risk']} [{item['severity']}]：{item['finding']} 动作：{item['action']}")
    lines.append("")
    lines.append("## Σ+ 输出")
    lines.append("")
    lines.append("- 当前真正增加的不是最终答案，而是一个可复用的状态包和审计路径。")
    lines.append("- 若要生成最终任务内容，必须先完成上述外部裁判或人工确认。")
    lines.append("- 失败路径已显式记录，避免后续把语言流畅度误认为系统健康。")
    lines.append("")
    lines.append("## 下一步协议")
    lines.append("")
    for idx, action in enumerate(_next_actions(packet, q_audit, route), start=1):
        lines.append(f"{idx}. {action}")
    lines.append("")
    return "\n".join(lines)


def _conclusion(packet: dict, q_audit: dict) -> str:
    if q_audit["status"] == "veto":
        return "原请求触发 Q 核否决；本轮不应直接按用户表面语言生成，而应先执行状态止损/审计协议。"
    if q_audit["status"] == "review_required":
        return "请求可继续，但必须带边界、验证和外部裁判；不得宣称已完成闭合。"
    return "请求可进入低风险处理，但输出仍需保留声明等级。"


def _next_actions(packet: dict, q_audit: dict, route: dict) -> list[str]:
    actions = []
    if q_audit["status"] == "veto":
        actions.append("停止原表面任务，改为输出 Q 核保护方案。")
    actions.append("补齐状态包未知项。")
    actions.append(f"执行路由要求的裁判：{', '.join(route['required_judges']) or '无'}。")
    actions.append("把通过和失败结果写入 failure ledger。")
    actions.append("再决定是否允许语言生成器输出面向用户的最终文本。")
    return actions
