from __future__ import annotations

import hashlib
import json
import re


TOPIC_SWITCH_MARKERS = (
    "换个话题",
    "換個話題",
    "切换话题",
    "切換話題",
    "另一个话题",
    "另一個話題",
    "new topic",
    "改聊",
    "改談",
    "下面改用",
    "接下来不谈",
    "接下來不談",
    "这一段到此为止",
    "這一段到此為止",
)
CAPSULE_COMPRESSION_THRESHOLD = 12
CAPSULE_MAX_USER_STATEMENTS = 20
CAPSULE_RECENT_USER_STATEMENTS = 8
DURABLE_STATE_MARKERS = (
    "代号",
    "代號",
    "称呼",
    "稱呼",
    "固定在",
    "定在",
    "安排在",
    "文件名",
    "檔名",
    "截止",
    "改为",
    "改為",
    "改成",
    "换成",
    "換成",
    "改期",
    "取消",
    "清单",
    "清單",
    "两件正事",
    "兩件正事",
    "已经完成",
    "已完成",
    "已经修完",
    "已修完",
    "已经买到",
    "已買到",
    "买到了",
    "買到了",
    "未完成",
    "还没",
    "還沒",
    "只写",
    "只寫",
    "只给",
    "只給",
    "不要",
    "格式",
    "照旧",
    "照舊",
    "其他不变",
    "其他不變",
    "译成",
    "譯成",
)


def _is_durable_user_statement(statement: str) -> bool:
    folded = statement.casefold()
    return any(marker in folded for marker in (*TOPIC_SWITCH_MARKERS, *DURABLE_STATE_MARKERS))


def _compress_user_statements(statements: list[str]) -> list[str]:
    if len(statements) <= CAPSULE_COMPRESSION_THRESHOLD:
        return statements[-CAPSULE_COMPRESSION_THRESHOLD:]
    recent_start = max(0, len(statements) - CAPSULE_RECENT_USER_STATEMENTS)
    recent_indices = list(range(recent_start, len(statements)))
    durable_indices = [
        index
        for index, statement in enumerate(statements[:recent_start])
        if _is_durable_user_statement(statement)
    ]
    available = CAPSULE_MAX_USER_STATEMENTS - len(recent_indices)
    if len(durable_indices) > available:
        if available <= 1:
            durable_indices = durable_indices[:available]
        else:
            durable_indices = [durable_indices[0], *durable_indices[-(available - 1):]]
    selected_indices = sorted({*durable_indices, *recent_indices})
    return [statements[index] for index in selected_indices]


def build_conversation_state_capsule(conversation: list[dict[str, str]]) -> dict:
    switch_index = 0
    for index in range(len(conversation) - 1, -1, -1):
        item = conversation[index]
        if item.get("role") == "user" and any(
            marker in str(item.get("content") or "").casefold()
            for marker in TOPIC_SWITCH_MARKERS
        ):
            switch_index = index
            break
    active = conversation[switch_index:]
    source_user_statements = [
        str(item.get("content") or "").strip()[:500]
        for item in active
        if item.get("role") == "user" and str(item.get("content") or "").strip()
    ]
    user_statements = _compress_user_statements(source_user_statements)
    canonical = json.dumps(user_statements, ensure_ascii=False, separators=(",", ":"))
    return {
        "user_authoritative": True,
        "topic_switch_applied": switch_index > 0,
        "active_user_statements": len(user_statements),
        "source_user_statements": len(source_user_statements),
        "retained_user_statements": len(user_statements),
        "dropped_user_statements": len(source_user_statements) - len(user_statements),
        "compression_applied": len(source_user_statements) > CAPSULE_COMPRESSION_THRESHOLD,
        "compression_strategy": "durable_state_plus_recent",
        "maximum_retained_user_statements": CAPSULE_MAX_USER_STATEMENTS,
        "user_statements": user_statements,
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def build_chat_prompt(
    current: str,
    conversation: list[dict[str, str]],
    result: dict,
    *,
    route_execution: dict | None = None,
) -> str:
    packet = result["packet"]
    q_audit = result["q_audit"]
    route = result["route"]
    bsigma = result["bsigma_audit"]
    role_labels = {"user": "用户", "assistant": "助手"}
    state_capsule = build_conversation_state_capsule(conversation)
    active_start = 0
    if state_capsule["topic_switch_applied"]:
        for index in range(len(conversation) - 1, -1, -1):
            item = conversation[index]
            if item.get("role") == "user" and any(
                marker in str(item.get("content") or "").casefold()
                for marker in TOPIC_SWITCH_MARKERS
            ):
                active_start = index
                break
    active_conversation = conversation[active_start:]
    recent = "\n".join(
        f"{role_labels[item['role']]}：{item['content']}" for item in active_conversation[-8:]
    )
    capsule_text = "\n".join(
        f"U{index}：{statement}"
        for index, statement in enumerate(state_capsule["user_statements"], start=1)
    ) or "无"
    required_judges = ", ".join(route["required_judges"]) or "无强制外部裁判"
    execution = route_execution or {}
    executed_facts = " | ".join(
        str(item)[:500] for item in execution.get("facts", [])[:4]
    ) or "无"
    execution_failures = " | ".join(
        str(item.get("message") or item.get("code"))[:300]
        for item in execution.get("failures", [])[:4]
    ) or "无"
    return "\n".join(
        [
            "你是物性AI的聊天助手。用户希望正常聊天：我问，你答。",
            "请像普通聊天产品一样直接、自然、简洁地回答，不要把内部审计流程当作正文展示。",
            "不要使用 emoji，不要用过度热情的客服腔，不要只确认页面状态而回避用户真正问题。",
            "除非用户主动询问机制，不要输出 PSM、Q 核、Omega、B_sigma、Sigma+、门控候选、状态链这些术语。",
            "物性AI的产品定位是先识别对象、状态、证据、未知项和边界，再生成语言；不要把它描述成只靠更多文本训练的高级语言模型。",
            "物性论术语只按以下项目定义回答：Q 核是不可击穿的目标与否决边界；φ 是已知事实、未知项和当前状态画像；Δσ 是推动状态变化的压力差；Π 是对象、角色、材料和依赖关系；η 是不确定性与长尾；Bσ 是对越级声明、证据缺口和边界擦除的审计；Σ+ 是带证据、边界和下一步动作的可交付结果。不要自行改写成能量、置信度或物理量。",
            "如果问题属于医疗、法律、交易、生产上线、隐私合规、外部发布等高风险场景：可以解释、列步骤、给草案，但必须明确不能替代专业判断或真实授权，不要给已验证、已批准或可直接执行的结论。",
            "法律问题优先提醒司法辖区、通知或诉讼期限、原始文件和合资格律师核对。",
            "法律期限、项目进度、部署流程和外部现况若没有可核验来源，不得自行补数字、模块、日期或已完成状态；明确写成未知并给出查证路径。",
            "研究问题必须区分内部结果与外部有效性；小样本要写不确定性；盲集失败要记录失败并换用新的未见数据，不能继续调到原盲集通过；相关性不能直接写成因果。",
            "交易问题中的压力测试指手续费、滑点、市场冲击、回撤和停止条件，不是网站并发负载测试。",
            "代码问题可以直接给最小代码片段；代码示例不等于生产放行，涉及上线时再补测试、监控、回滚和负责人审批。",
            "用户要求绝对保证、绝不失败或零风险时，要直接说明无法保证，再提供降低失败概率和验证风险的做法。涉及食物过敏时必须考虑配料标签和交叉接触。",
            "医疗检查准备必须以医院的预约说明为准；未确认已经安排检查时，不要擅自要求停药、禁水或长时间空腹。",
            "多轮问题必须使用前文给出的对象、材料和约束，不要把当前追问当成无上下文的新问题。",
            "状态胶囊只包含当前话题段的用户原话，权威高于助手历史：按时间顺序理解，用户后来的明确更正覆盖旧值；从任务清单中扣除用户已明确完成的事项；‘照旧’或‘其他不变’继承用户先前给出的格式约束。",
            "发生明确话题切换后，不得把旧话题的对象、风险或边界带入新话题；只使用状态胶囊中的当前话题段。",
            "回答前重新检查用户问题中的每一个明确要求；有多个问题、限制或输出格式时要逐项覆盖，并在结束前给出具体结论或下一步。",
            "科学解释要沿用用户已给出的正确前提，不要为了流畅改写成相反机制；例如水结冰是形成较疏松的开放晶格，不是晶格被破坏。",
            "如果问题是普通闲聊、写作、解释、计划、代码思路，则直接帮助用户。",
            "中文回答，优先繁简混合可读，先给结论，控制在 300 字以内。",
            "",
            "最近对话（保留角色）：",
            recent,
            "",
            "当前用户问题：",
            current,
            "",
            "当前话题的用户权威状态胶囊（只用于回答，不要复述标签）：",
            capsule_text,
            "",
            "内部状态，只用于把握风险，不要原样输出：",
            f"- domain: {packet['domain']}",
            f"- risk_level: {packet['omega']['risk_level']}",
            f"- q_status: {q_audit['status']}",
            f"- route: {route['route']}",
            f"- required_judges: {required_judges}",
            f"- bsigma_status: {bsigma['status']}",
            f"- route_execution_status: {execution.get('status', 'not_executed')}",
            f"- route_execution_facts: {executed_facts}",
            f"- route_execution_failures: {execution_failures}",
            "- 工具或来源失败时不得写成已经核验；证据冲突时不得自行选择较顺口的一边。",
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
