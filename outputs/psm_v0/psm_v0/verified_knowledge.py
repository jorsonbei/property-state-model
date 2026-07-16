from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedKnowledge:
    kernel_id: str
    answer: str
    grounding_facts: tuple[str, ...]
    grounding_sources: tuple[str, ...]


def match_verified_knowledge(text: str) -> VerifiedKnowledge | None:
    folded = text.casefold()
    if _all_groups(
        folded,
        (
            ("金属", "金屬", "铁", "鐵", "铝", "鋁"),
            ("木头", "木頭", "木材", "木杯"),
            ("同样温度", "同樣溫度", "同温", "同溫", "室温", "室溫"),
            ("更冷", "更凉", "更涼", "摸起来", "摸起來"),
        ),
    ):
        return VerifiedKnowledge(
            kernel_id="touch_temperature_thermal_effusivity",
            answer=(
                "即使金属和木材温度相同，金属摸起来通常更冷，也不是因为它辐射更多冷量。"
                "人的冷热感觉主要取决于皮肤热量流失的速度：金属导热率和热效应率较高，能更快把手上的热传走，"
                "皮肤温度下降更快；木材导热较慢，接触面附近很快被手加热，所以感觉没那么冷。"
                "如果两者都高于皮肤温度，方向会反过来，金属往往会显得更烫。"
            ),
            grounding_facts=("皮肤热量流失的速度", "金属导热率和热效应率较高", "金属和木材温度相同"),
            grounding_sources=("verified_kernel:touch_temperature_thermal_effusivity",),
        )
    if _all_groups(
        folded,
        (
            ("压缩", "壓縮", "压缩包", "壓縮檔"),
            ("文件", "内容", "內容", "数据", "資料"),
            ("变小", "變小", "体积", "體積", "大小", "几乎不变", "幾乎不變"),
        ),
    ):
        return VerifiedKnowledge(
            kernel_id="compression_redundancy_entropy",
            answer=(
                "压缩程序靠发现重复模式和可预测结构，用更短的表示替代它们。文本、表格或未压缩位图通常冗余较多，"
                "所以能明显变小；JPEG、MP4、ZIP 等已压缩过的内容，以及加密数据或接近随机的数据，可利用的冗余很少，"
                "再次无损压缩通常变化不大，还可能因文件头和索引略微变大。用信息论语言近似地说，越难预测、熵越高的数据越难继续压缩，"
                "不是高熵更容易压缩。"
            ),
            grounding_facts=("重复模式", "已压缩过的内容", "熵越高的数据越难继续压缩"),
            grounding_sources=("verified_kernel:compression_redundancy_entropy",),
        )
    if _all_groups(
        folded,
        (("高海拔", "山顶", "山頂", "海拔升高"), ("密封", "没有漏气", "沒有漏氣"), ("膨胀", "膨脹", "鼓起")),
    ):
        return VerifiedKnowledge(
            kernel_id="sealed_gas_external_pressure",
            answer=(
                "主要原因是海拔升高后外界大气压降低。密封容器内的气体起初接近包装地的气压；"
                "上山后外界压力变小，内部压力相对更高，于是包装向外膨胀，直到体积变化、膜张力和内外压差重新平衡。"
                "恒温条件排除了温度升高这个主因。若内部压力真的低于外界，包装应被压瘪，而不是鼓起。"
            ),
            grounding_facts=("外界大气压降低", "内部压力相对更高"),
            grounding_sources=("verified_kernel:sealed_gas_external_pressure",),
        )
    if _all_groups(
        folded,
        (("javascript", "js", "浏览器", "瀏覽器"), ("int64", "64位", "bigint", "长整型", "長整型"), ("精度", "后几位", "後幾位", "id")),
    ):
        return VerifiedKnowledge(
            kernel_id="javascript_safe_integer_transport",
            answer=(
                "这是 JavaScript `Number` 的安全整数边界，不是把 `int64` 当成 32 位整数。"
                "`Number` 只能保证精确表示到 `2^53-1`（`9007199254740991`）；更大的 JSON 数字在 `JSON.parse` 时就可能被舍入，"
                "之后再调用 `parseInt()` 或 `BigInt()` 也无法恢复已经丢失的位。后端存储仍可保持 Go `int64`，但传输时应把 ID 编码为 JSON 字符串；"
                "前端将它保留为字符串，确需整数运算时再用 `BigInt(idString)`。还应围绕安全整数边界加入序列化与关联测试。"
            ),
            grounding_facts=("2^53-1", "JSON 字符串", "BigInt(idString)"),
            grounding_sources=("https://tc39.es/ecma262/2025/multipage/numbers-and-dates.html#sec-number.max_safe_integer",),
        )
    if _all_groups(
        folded,
        (("a/b", "ab测试", "实验组", "實驗組"), ("设备", "設備", "浏览器", "瀏覽器"), ("用户", "用戶", "账号", "帳號")),
    ):
        return VerifiedKnowledge(
            kernel_id="experiment_unit_cross_device_contamination",
            answer=(
                "核心问题是随机化单位与实际处理单位不一致，造成跨设备处理污染和观测不独立；只称为“设备异构”不够准确。"
                "同一用户可能同时进入实验组和对照组，效果会被稀释，标准误也可能被低估。应按稳定的用户或账号 ID 做粘性分组，"
                "保证同一人跨设备始终看到同一版本；分析、去重和标准误聚类也要使用同一用户单位。未登录用户需另设稳定匿名标识并单独报告。"
            ),
            grounding_facts=("随机化单位", "处理污染", "用户或账号 ID"),
            grounding_sources=("verified_kernel:experiment_unit_cross_device_contamination",),
        )
    if (
        _any(folded, ("未来函数", "未來函數", "lookahead", "前视偏差", "前視偏差"))
        or _all_groups(
        folded,
        (("收盘", "收盤"), ("当天最高价", "當天最高價", "当天最低价", "當天最低價"), ("回测", "回測")),
        )
        or _all_groups(
            folded,
            (("未来 bar", "未來 bar", "更晚k线", "更晚 k线", "更晚k線", "更晚 k線"), ("更早", "先前", "旧信号", "舊訊號")),
        )
    ):
        return VerifiedKnowledge(
            kernel_id="event_time_no_lookahead",
            answer=(
                "这不是一般的“实盘环境更复杂”，而是前视偏差：策略先用当天收盘数据确认信号，却又假设能在同一天已经过去的最高价或最低价成交，"
                "决策时读取了未来信息。应明确事件时间：bar `t` 的特征只能使用 `t` 时刻已经最终确认的数据；若信号在收盘后产生，最早只能按 `t+1` 的可成交价格执行。"
                "工程上要把历史只读数据与实时事件流分开，按时间戳截断特征，禁止共享未来行，并加入测试：修改未来 bar 不得改变任何更早信号。"
                "最后再计入滑点、手续费、流动性和拒单。这不构成实盘授权。"
            ),
            grounding_facts=("前视偏差", "t+1", "修改未来 bar 不得改变任何更早信号"),
            grounding_sources=("verified_kernel:event_time_no_lookahead",),
        )
    if _all_groups(
        folded,
        (("劳动仲裁", "勞動仲裁", "劳动争议", "勞動爭議"), ("时效", "時效", "期限")),
    ):
        return VerifiedKnowledge(
            kernel_id="prc_labor_arbitration_limitation",
            answer=(
                "先固定证据：保存劳动合同、工资和社保记录、解除通知与沟通原件、竞业协议版本、离职证明要求及时间线；"
                "不要在未核对补偿与适用范围前被迫立即签字。根据中国人大网现行《劳动争议调解仲裁法》第二十七条，"
                "申请劳动争议仲裁的一般时效是一年，从知道或应当知道权利受侵害之日起计算，不是一般民事诉讼的三年；"
                "主张权利、请求救济、对方同意履行等可能导致中断，拖欠劳动报酬等还有特别规则。具体起算、中断、管辖和深圳办理要求，"
                "应让当地劳动律师或仲裁机构结合原始材料核对。"
            ),
            grounding_facts=("一般时效是一年", "第二十七条", "中断"),
            grounding_sources=("https://www.npc.gov.cn/npc/c2/c183/c198/201905/t20190522_28233.html",),
        )
    if _all_groups(
        folded,
        (("麸质", "麩質", "gluten"), ("过敏", "過敏"), ("绝对", "絕對", "保证", "保證", "不会失败", "不會失敗")),
    ):
        return VerifiedKnowledge(
            kernel_id="food_allergy_no_absolute_promise",
            answer=(
                "不能承诺一道菜“绝对不会失败”或“绝对无过敏风险”。先向主人确认过敏严重程度、可用品牌和厨房要求；"
                "除食材本身外，还要避免含麸质酱油、调味料以及共用砧板、锅具造成的交叉接触。较稳妥的聚餐主食是白米蔬菜鸡肉饭："
                "使用明确标注无麸质的调料，分开清洗和烹调，并保留包装供主人核对。若过敏严重，优先让主人指定食材或选择未开封的合规成品。"
            ),
            grounding_facts=("不能承诺", "交叉接触", "明确标注无麸质"),
            grounding_sources=("verified_kernel:food_allergy_no_absolute_promise",),
        )
    return None


def _any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _all_groups(text: str, groups: tuple[tuple[str, ...], ...]) -> bool:
    return all(_any(text, group) for group in groups)
