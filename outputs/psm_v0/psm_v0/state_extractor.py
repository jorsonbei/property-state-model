from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from . import VERSION


DOMAIN_KEYWORDS = {
    "medical": [
        "医疗",
        "醫療",
        "诊断",
        "診斷",
        "症状",
        "症狀",
        "胸口痛",
        "胸痛",
        "出冷汗",
        "发烧",
        "發燒",
        "高烧",
        "高燒",
        "吃药",
        "吃藥",
        "治疗",
        "治療",
        "急救",
        "医院",
        "醫院",
        "医生",
        "醫生",
    ],
    "legal": ["法律", "律师", "律師", "合同", "合約", "起诉", "起訴", "诉讼", "訴訟", "合规", "合規", "违法", "違法", "管辖区", "管轄區"],
    "trading": ["交易", "股票", "期货", "期貨", "实盘", "實盤", "回测", "回測", "盈亏", "盈虧", "止损", "止損", "回撤", "滑点", "滑點", "手续费", "手續費", "因子"],
    "code_engineering": ["代码", "代碼", "程序", "程式", "上线", "上線", "生产环境", "生產環境", "bug", "数据库", "資料庫", "python", "api", "go live", "production"],
    "wuxing_theory": ["物性论", "物性論", "物性AI", "物性 AI", "物性模型", "物性项目", "物性項目", "Q 核", "Q核", "Ω", "Δσ", "Π", "B_σ", "Σ+", "NoTargetRead", "judge-only", "外部世界等价读取", "外部世界等價讀取", "global equivalence"],
    "research": ["论文", "論文", "实验", "實驗", "数据集", "數據集", "原始数据", "原始數據", "样本", "樣本", "引用", "公式", "推导", "推導", "复演", "復演", "后验拟合", "後驗擬合", "过拟合", "過擬合", "预注册", "預註冊", "NoBackfit", "Fresh Holdout", "fully proved"],
    "business_decision": ["公司", "现金流", "团队", "融资", "客户", "产品", "破产", "增长", "战略"],
    "writing": ["写一份", "写一段", "写一篇", "文章", "演讲稿", "文案", "润色", "标题", "标语", "脚本", "翻译"],
}

DOMAIN_META_OR_NEGATION = {
    "trading": ["不涉及交易", "不涉及交易建议", "和交易无关", "不做交易建议", "不给交易建议"],
}


Q_CORE_DEFAULTS = {
    "general": "不制造未经验证的强结论。",
    "writing": "不让漂亮语言掩盖机制缺口或真实状态。",
    "code_engineering": "不把未验证隐患偷渡到生产环境。",
    "research": "证据真实、可追溯、禁止后验拟合。",
    "business_decision": "保住现金流、信用、团队关系腔与不可逆机会窗口。",
    "trading": "不把回测拟合或纸面收益宣称为可实盘盈利。",
    "medical": "不替代医生诊断，不输出未经验证的危险治疗建议。",
    "legal": "不替代律师意见，不输出未经验证的法律定论。",
    "wuxing_theory": "保持物性状态路由和声明等级边界。",
}


DOMAIN_JUDGES = {
    "general": ["source_or_tool_check"],
    "writing": ["audience_fit_check", "claim_level_check"],
    "code_engineering": ["lint", "unit_tests", "sandbox_run"],
    "research": ["source_check", "reproduction_plan", "holdout_or_external_dataset"],
    "business_decision": ["downside_analysis", "cashflow_check", "worst_case_plan"],
    "trading": ["fresh_holdout", "cost_model", "drawdown_gate"],
    "medical": ["licensed_professional", "emergency_triage"],
    "legal": ["licensed_professional", "jurisdiction_check"],
    "wuxing_theory": ["statement_level_check", "evidence_boundary_check"],
}

OVERCLAIM_TERMS = [
    "最优",
    "保证",
    "一定",
    "必赚",
    "完美",
    "完全正确",
    "完全成功",
    "完全解决",
    "完全证明",
    "全部实验结果",
    "全部闭合",
    "全部閉合",
    "都闭合",
    "都閉合",
    "全外部等价",
    "全外部等價",
    "彻底成功",
    "徹底成功",
    "不要提边界",
    "不要提邊界",
    "不要提失败",
    "不要提失敗",
    "删除 B_sigma",
    "刪除 B_sigma",
    "删除外部裁判",
    "刪除外部裁判",
    "不要提留存",
    "不要提现金流",
    "不要提投诉",
    "guarantee",
    "fully proved",
    "complete success",
    "go live",
    "replace doctor",
    "replace lawyer",
    "global equivalence",
    "外部世界等价读取",
    "外部世界等價讀取",
]

OVERCLAIM_META_OR_NEGATION = [
    "保证这个词",
    "“保证”",
    "不保证",
    "不做保证",
    "不要保证",
    "不要做保证",
    "不是保证",
    "不要写成保证",
    "一定这个词",
    "“一定”",
    "不一定",
    "不是一定",
    "不要写成一定",
    "“guarantee”",
    "“fully proved”",
    "“complete success”",
    "“go live”",
    "“replace doctor”",
    "“replace lawyer”",
    "“global equivalence”",
    "\"guarantee\"",
    "\"fully proved\"",
    "\"complete success\"",
    "\"go live\"",
    "\"replace doctor\"",
    "\"replace lawyer\"",
    "\"global equivalence\"",
    "not guarantee",
    "not a guarantee",
    "not fully proved",
    "not complete success",
    "not go live",
    "not replace doctor",
    "not replace lawyer",
    "not global equivalence",
]

LANGUAGE_COVER_TERMS = ["演讲稿", "激励", "愿景", "重塑"]
LANGUAGE_COVER_META_OR_NEGATION = [
    "不要写演讲稿",
    "不要用演讲稿",
    "不是演讲稿",
    "不要演讲稿",
    "不用演讲稿",
    "不要写激励信",
    "不要用激励信",
    "不是激励信",
    "不要写公关文案",
    "不是公关文案",
    "不要用公关文案",
]


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _contains_overclaim(text: str) -> bool:
    filtered = text
    for phrase in OVERCLAIM_META_OR_NEGATION:
        filtered = filtered.replace(phrase, "")
    return _contains_any(filtered, OVERCLAIM_TERMS)


def _contains_language_cover(text: str) -> bool:
    filtered = text
    for phrase in LANGUAGE_COVER_META_OR_NEGATION:
        filtered = filtered.replace(phrase, "")
    return _contains_any(filtered, LANGUAGE_COVER_TERMS)


def _filter_domain_meta_or_negation(text: str, domain: str) -> str:
    filtered = text
    for phrase in DOMAIN_META_OR_NEGATION.get(domain, []):
        filtered = filtered.replace(phrase, "")
    return filtered


def infer_domain(text: str) -> str:
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if _contains_any(_filter_domain_meta_or_negation(text, domain), keywords):
            return domain
    return "general"


def infer_facts(text: str) -> list[str]:
    facts: list[str] = []
    if _contains_any(text, ["现金流", "現金流"]):
        facts.append("请求中出现现金流压力。")
    if _contains_any(text, ["两周", "2周", "兩週", "两星期"]):
        facts.append("请求中出现短时间窗口：约两周。")
    if _contains_any(text, ["士气", "士氣", "团队", "團隊"]):
        facts.append("请求中出现团队关系腔压力。")
    if _contains_any(text, ["卖不出去", "賣不出去", "没有客户", "沒有客戶"]):
        facts.append("请求中出现产品/市场需求压力。")
    if _contains_any(text, ["上线", "上線", "生产环境", "生產環境", "實盤", "实盘", "诊断", "診斷", "治疗", "治療"]):
        facts.append("请求可能进入高风险真实世界执行。")
    if not facts:
        facts.append("仅从原始请求可见，仍缺少外部事实。")
    return facts


def infer_unknowns(domain: str) -> list[str]:
    base = ["缺少可核验原始证据。", "缺少失败边界与停止条件。"]
    if domain == "business_decision":
        return base + ["缺少现金余额、 burn rate、债务、订单、团队成本。"]
    if domain == "code_engineering":
        return base + ["缺少运行环境、依赖版本、测试覆盖、部署约束。"]
    if domain == "research":
        return base + ["缺少数据来源、样本窗口、预注册假设、外部裁判。"]
    if domain == "trading":
        return base + ["缺少滑点、手续费、容量、Fresh Holdout、风险预算。"]
    if domain == "medical":
        return base + ["缺少专业诊断、病史、检查结果、急症排查。"]
    return base


def infer_risk_level(domain: str, text: str) -> str:
    if domain in {"medical", "legal", "trading"}:
        return "critical"
    critical_terms = [
        "实盘",
        "實盤",
        "生产环境",
        "生產環境",
        "上线",
        "上線",
        "急救",
        "破产",
        "抵押",
        "高利贷",
        "绕过登录",
        "绕过权限",
        "读取用户数据库",
        "越权",
    ]
    high_terms = ["现金流", "現金流", "科研", "论文", "論文", "实验", "實驗", "代码", "代碼", "投资", "投資", "交易", "公司", "团队", "團隊"]
    if _contains_any(text, critical_terms):
        return "critical"
    if domain in {"business_decision", "code_engineering", "research", "wuxing_theory"}:
        return "high"
    if _contains_any(text, high_terms):
        return "high"
    if domain == "writing":
        return "low"
    return "medium"


def infer_delta_sigma(text: str, domain: str) -> list[str]:
    pressures: list[str] = []
    if _contains_any(text, ["现金流", "破产", "亏损", "兩週", "两周"]):
        pressures.append("资金/时间压力正在形成强 Δσ。")
    if _contains_any(text, ["团队", "士气", "信任", "离职"]):
        pressures.append("团队 Π 关系腔可能漏气。")
    if _contains_any(text, ["卖不出去", "客户", "市场", "需求"]):
        pressures.append("产品与市场之间存在需求势差。")
    if _contains_any(text, ["上线", "上線", "生产环境", "生產環境", "实盘", "實盤", "诊断", "診斷", "治疗", "治療"]):
        pressures.append("输出可能跨入真实世界，错误成本高。")
    if not pressures:
        pressures.append(f"{domain} 任务存在未量化压力差，需要补证据。")
    return pressures


def infer_pi_cavity(domain: str) -> dict:
    actors = ["用户", "PSM_V0"]
    artifacts = ["原始请求", "状态包", "Σ+ 报告"]
    dependencies = ["证据来源", "外部裁判", "失败入账"]
    if domain == "business_decision":
        actors += ["团队", "客户", "债权人/投资人"]
        artifacts += ["现金流表", "产品数据", "组织沟通记录"]
        dependencies += ["现金余额", "成本结构", "市场需求", "信任状态"]
    elif domain == "code_engineering":
        actors += ["开发者", "用户", "运行环境"]
        artifacts += ["代码", "测试", "依赖清单"]
        dependencies += ["数据库", "权限", "部署环境", "回滚路径"]
    elif domain == "research":
        actors += ["研究者", "复演者", "外部裁判"]
        artifacts += ["数据集", "公式", "实验日志"]
        dependencies += ["预注册假设", "原始数据", "残差", "复演入口"]
    return {"actors": actors, "artifacts": artifacts, "dependencies": dependencies}


def infer_bsigma_risks(text: str, domain: str) -> list[dict]:
    risks: list[dict] = []
    if _contains_language_cover(text):
        risks.append(
            {
                "risk": "language_cover",
                "reason": "请求可能用漂亮语言覆盖真实状态压力。",
                "severity": "high" if domain == "business_decision" else "medium",
            }
        )
    if _contains_overclaim(text):
        risks.append(
            {
                "risk": "overclaim",
                "reason": "请求中存在强确定性输出倾向。",
                "severity": "high",
            }
        )
    if domain in {"research", "trading"}:
        risks.append(
            {
                "risk": "backfit",
                "reason": "该领域天然存在后验拟合或偷看答案风险。",
                "severity": "high",
            }
        )
    if domain in {"medical", "legal"}:
        risks.append(
            {
                "risk": "external_authority_required",
                "reason": "该领域需要专业外部裁判，不能由模型直接定论。",
                "severity": "high",
            }
        )
    if domain == "code_engineering":
        risks.append(
            {
                "risk": "untested_code",
                "reason": "代码输出若未运行，可能成为工程假光。",
                "severity": "high",
            }
        )
    if not risks:
        risks.append({"risk": "unverified_claim", "reason": "缺少外部验证。", "severity": "medium"})
    return risks


def infer_statement_level(risk_level: str) -> str:
    if risk_level == "low":
        return "C1"
    if risk_level == "medium":
        return "C2"
    if risk_level == "high":
        return "C3"
    return "C4"


def build_state_packet(user_request: str) -> dict:
    domain = infer_domain(user_request)
    risk_level = infer_risk_level(domain, user_request)
    facts = infer_facts(user_request)
    unknowns = infer_unknowns(domain)
    q_primary = Q_CORE_DEFAULTS[domain]
    return {
        "packet_id": str(uuid4()),
        "version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user_request": user_request,
        "domain": domain,
        "phi_state": {
            "summary": "已将原始请求降级为状态画像，禁止直接按语言表面执行。",
            "facts": facts,
            "unknowns": unknowns,
        },
        "q_core": {
            "primary": q_primary,
            "protected_boundaries": [
                "不制造假光。",
                "不把未验证写成已验证。",
                "不把局部闭合写成全局闭合。",
            ],
            "veto_conditions": [
                "请求会击穿 Q 核。",
                "请求要求用语言掩盖真实状态。",
                "高风险任务拒绝外部裁判。",
            ],
        },
        "omega": {
            "risk_level": risk_level,
            "time_scale": "request_level_unknown",
            "validation_scale": "external_judge_required" if risk_level in {"high", "critical"} else "light_check",
            "cost_scale": "unknown_total_cost",
        },
        "delta_sigma": {
            "pressures": infer_delta_sigma(user_request, domain),
            "missing_pressure_data": infer_unknowns(domain),
        },
        "pi_cavity": infer_pi_cavity(domain),
        "eta": {
            "uncertainties": infer_unknowns(domain),
            "tail_events": ["长尾失败模式尚未枚举。", "外部环境突变尚未建模。"],
        },
        "bsigma_risks": infer_bsigma_risks(user_request, domain),
        "external_judges": DOMAIN_JUDGES[domain],
        "statement_level": infer_statement_level(risk_level),
    }
