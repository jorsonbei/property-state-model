from __future__ import annotations

import re


def build_chat_prompt(
    current: str,
    conversation: list[dict[str, str]],
    result: dict,
) -> str:
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    role_labels = {"user": "用户", "assistant": "助手"}
    recent = "\n".join(
        f"{role_labels[item['role']]}：{item['content']}" for item in conversation[-8:]
    )
    required_judges = ", ".join(route["required_judges"]) or "无强制外部裁判"
    return "\n".join(
        [
            "你是物性AI的聊天助手。用户希望正常聊天：我问，你答。",
            "请像普通聊天产品一样直接、自然、简洁地回答，不要把内部审计流程当作正文展示。",
            "不要使用 emoji，不要用过度热情的客服腔，不要只确认页面状态而回避用户真正问题。",
            "除非用户主动询问机制，不要输出 PSM、Q 核、Omega、B_sigma、Sigma+、门控候选、状态链这些术语。",
            "物性AI的产品定位是先识别对象、状态、证据、未知项和边界，再生成语言；不要把它描述成只靠更多文本训练的高级语言模型。",
            "如果问题属于医疗、法律、交易、生产上线、隐私合规、外部发布等高风险场景：可以解释、列步骤、给草案，但必须明确不能替代专业判断或真实授权，不要给已验证、已批准或可直接执行的结论。",
            "法律问题优先提醒司法辖区、通知或诉讼期限、原始文件和合资格律师核对。",
            "如果问题是普通闲聊、写作、解释、计划、代码思路，则直接帮助用户。",
            "中文回答，优先繁简混合可读，先给结论，控制在 300 字以内。",
            "",
            "最近对话（保留角色）：",
            recent,
            "",
            "当前用户问题：",
            current,
            "",
            "内部状态，只用于把握风险，不要原样输出：",
            f"- domain: {packet['domain']}",
            f"- risk_level: {packet['omega']['risk_level']}",
            f"- q_status: {q_audit['status']}",
            f"- route: {route['route']}",
            f"- required_judges: {required_judges}",
            f"- bsigma_status: {bsigma['status']}",
        ]
    )


def sanitize_model_answer(text: str) -> tuple[str, bool]:
    reasoning_leak = bool(re.search(r"<think>|</think>", text, flags=re.IGNORECASE))
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<think>.*\Z", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"^\s*(?:analysis|reasoning)\s*[:：]\s*", "", cleaned, flags=re.IGNORECASE)
    emoji_ranges = ((0x1F300, 0x1FAFF), (0x2600, 0x27BF))
    cleaned = "".join(
        char
        for char in cleaned
        if not any(start <= ord(char) <= end for start, end in emoji_ranges)
    )
    return cleaned.strip(), reasoning_leak
