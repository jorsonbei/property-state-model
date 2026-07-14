# PSM V0 蓝图

## 目标

PSM V0 的目标不是替代大语言模型，而是建立一个外层状态操作系统，让任何语言模型、工具链或人工专家在回答之前，必须先经过物性状态路由。

核心原则：

```text
不要先回答。先接状态。
不要先优化语言。先守 Q 核。
不要把内部自洽当成功。先过外部裁判。
不要隐藏失败。失败必须入账。
```

## 最小闭环

```text
User Request
-> State Extractor
-> Q Core Auditor
-> Omega Router
-> Pi Cavity Builder
-> B_sigma Auditor
-> Sigma Reporter
```

### 1. State Extractor

将用户语言转成 `state_packet`。它至少要抽取：

- `domain`：任务领域。
- `phi_state`：真实状态画像。
- `q_core`：不可背叛的底线。
- `omega`：时间、风险、成本、验证刻度。
- `delta_sigma`：真实压力差。
- `pi_cavity`：相关对象与依赖关系。
- `eta`：未知、意外、长尾因素。
- `bsigma_risks`：假光风险。

### 2. Q Core Auditor

只做底线判断，不负责讨好用户。

输出三种状态：

- `pass`：可继续。
- `review_required`：必须带边界或验证。
- `veto`：拒绝生成原请求，改为输出止损/降级/保护动作。

### 3. Omega Router

按刻度选择处理路线：

- 低风险语言任务：直接语言处理。
- 事实任务：检索和来源核验。
- 代码任务：生成、静态检查、沙盒运行。
- 科研任务：证据来源、NoBackfit、复演协议。
- 金融/交易任务：Fresh Holdout、成本、风险闸。
- 医疗/法律/生命安全任务：外部专业裁判与人类确认。

### 4. Pi Cavity Builder

把任务从局部问题扩展成关系腔，列出：

- 关键对象。
- 关键依赖。
- 资源与约束。
- 外部裁判。
- 失败传播路径。

### 5. B_sigma Auditor

检测假光：

- 幻觉引用。
- 未验证代码。
- 单指标假成功。
- 跨刻度套用。
- 后验拟合。
- 把草案写成已验证。
- 把局部闭合写成全局闭合。

### 6. Sigma Reporter

最终输出不是普通答案，而是 `Σ+ report`：

- 结论。
- 适用边界。
- 证据链。
- 风险与失败路径。
- 外部裁判状态。
- 下一步协议。
- 声明等级。

## V0 之后

### V1：状态编码器

训练模型从文本、代码、日志、表格、实验报告中抽取 `Q / Ω / φ_state / Δσ / Π / η / B_sigma / Σ+`。

### V2：物性原生模型

训练目标不再只是 next-token prediction，而是：

```text
next token
+ state variable prediction
+ failure mode prediction
+ external judge outcome prediction
+ B_sigma minimization
+ verified Sigma+ maximization
```
