# 产品形态 —— WebAgentFlow

> 本文是 WebAgentFlow 的**产品总纲** —— 当前大家对"这个产品是什么"
> 的共同理解。把它当成大方向参考，而不是死板的"宪法"。
>
> - 产品**方向**变了（新生命周期阶段、新 Agent 角色、不变量调整），先更新
>   本文，再改代码。
> - 日常实现细节不需要每次都回来改这份文档 —— 保持整体形态一致就好。
> - 如果一个提议在本文的生命周期阶段 / Agent 里都找不到位置、而且感觉像是
>   产品级的新增（不是实现细节），**先停下问用户**再写代码。

---

## 术语（生命周期阶段 vs 交付里程碑）

过去文档里同时把"页面产品生命周期"和"工程路线图"都叫 Phase，导致
后续规划很容易混淆。从本文开始，统一使用以下术语：

- **生命周期阶段 L1 / L2 / L3** —— 一个页面在 WebAgentFlow 中固定
  经历的产品生命周期：自主学习 → 用户引导学习 → 实际工作。定义在
  本文档 §3–§6。固定三个，**永远不会增加**。
- **交付里程碑 M10 / M11 / ...** —— 工程路线图里程碑，记录在
  [`roadmap.zh.md`](./roadmap.zh.md)，编号会持续增长。现有迭代目录
  仍沿用 `docs/iterations/phase-10/` 这类历史路径，避免目录迁移噪音，
  但路线图正文应称为 **M10**。
- **§N** —— 本文档内部的章节号，仅用于交叉引用。

新的产品规划里不要再裸写"Phase 3"或"Phase 10"。请写
"L3 Actual Work / L3 实际工作" 或 "M10 Path Asset Foundation /
M10 路径资产基础"。

---

## 1. 一句话

WebAgentFlow 的目标是代替用户在网页上敲键盘点鼠标：先把页面学明白，
然后**逐步走向**"由系统自己开真实浏览器去完成用户的任务" —— 而**不是**
让大模型在每一步去读 HTML、决定点哪里。

## 2. 系统角色边界

在谈 L1/L2/L3 之前，先讲**谁干什么**。这些边界在一连串对话里很容易
被忘掉，然后系统就悄悄地跑偏。

- **WebAgentFlow 引擎**（代码 + 产品内 Agent）—— 运行时。取页面、
  分析、用 Playwright 尝试操作、跑 Supervisor。**运行时真正干活的
  是它**。
- **Workbench 界面**（`/exploration/autonomous`）—— 操作者的观察
  窗口。用户在这里**观察**引擎的动作、**手动触发**运行、**接受或
  拒绝**结果。它不是引擎，是引擎前面的那块玻璃。
- **用户** —— 操作者。触发运行、复核结果、做纠正。在 L2（用户
  引导学习）里用户是**页面的真正操作者**，不只是复核者。默认前提是：
  操作者有权操作他要求 WebAgentFlow 操作的目标网页。
- **目标网页** —— 拥有自己的 cookies、`localStorage`、session 状态、
  权限与授权结果。WebAgentFlow 不替代这些职责。
- **AI 编码 Agent**（Claude Code、Codex 等）—— 负责**开发和维护
  引擎**。**不在运行时链路里**。不得代替用户跑应用再把结果汇报
  回去 —— 那会毁掉用户区分"应用真的在工作"和"AI 编码 Agent 用脚手架
  糊弄"的能力。（硬约束见 `CLAUDE.zh.md` §"AI 编码 Agent —— 执行
  边界"。）

**运行时环境**：引擎驱动的是应用自带的**独立 Chromium**（通过
`playwright install chromium` 安装），**不是用户自己的浏览器**。按
重要性排：

1. **安全 / 隔离** —— 用户的 cookies、登录态、书签、扩展、浏览历史
   不会被引擎碰到；反过来，引擎在它自己的 Chromium 里做的事也不会
   渗到用户真实浏览器里。企业用户尤其在意这点，因为数据卫生是硬性
   要求。
2. **环境受控** —— 所有用户跑的是同一份 Chromium 版本，没有用户侧
   扩展或 profile 状态带来的噪音。
3. **扩展空间** —— 为引擎自己的交互层（Agent 聊天 overlay、探针）
   留出注入面，也方便以后装插件或做更深的浏览器定制。

WebAgentFlow **不**维护自己的 user / account model。它不实现
credential vault、多租户授权、跨用户授权、托管式操作者数据管理、
商业化收费或用量管控。这些不是项目自有身份层的路线图。

Session 状态由操作者和目标网页负责。页面需要既有 session 时，操作者
通过目标网页自己的流程，在引擎控制的浏览器上下文中建立或刷新状态。
Cookies、`localStorage`、session 过期和目标网页权限都属于目标网页的
职责。登录态失效、页面跳回登录、权限不足或操作失败时，运行进入
恢复 / 用户沟通流程。

拿不准一个新功能归谁时，先把它放到这根轴上：是引擎逻辑、workbench
玻璃、用户工作流，还是开发者工具？不同轴，不同的评审标准。

### 2.1 Runtime Conversation Surface / 运行时沟通入口

用户始终和 **WebAgentFlow** 这个应用沟通，而不是直接和 Agent D、
Agent F、Agent G、Agent H 或其他内部子 Agent 沟通。内部 Agent 名称
是实现角色；运行时产品表面以统一的 WebAgentFlow 视角说话。

第一版有用的沟通入口可以 **CLI-first**。CLI-first 是为了先跑通完整
产品闭环：任务输入、执行前确认、失败恢复、用户中断、教学模式对话和
最终结果汇报。有开发能力的用户也可以通过 CLI / API 把 WebAgentFlow
接入自己的系统，或自建操作台。

这个运行时沟通入口不是 M16 的外部调度接口，也不是今天的
`verify-scenario` 开发验证工具。它是产品运行时入口。

### 2.2 Conversation Orchestrator / Dispatcher / 会话编排器

运行时对话需要一个代码侧 **Conversation Orchestrator / Dispatcher**。
它不是新的万能 LLM Agent，而是 session controller 和内部 Agent router。

职责：

- 维护 session state
- 接收用户消息和 engine events
- 在正确边界把工作路由给 Agent D / E / F / G / H
- 管理 confirmation、pause、resume、abort、takeover 和 teaching mode
- 强制执行 L3 不变量：大模型不进入逐步浏览器执行循环
- 用 WebAgentFlow 视角统一输出给用户，而不是暴露各个内部 Agent 的口吻

示例状态：

- `idle`
- `task_planning`
- `awaiting_confirmation`
- `executing_path`
- `recovery_dialogue`
- `abort_dialogue`
- `guided_teaching`
- `user_demonstration`
- `reporting_result`

## 3. 页面的三个生命周期阶段

每个页面在 WebAgentFlow 的生命周期里都要经历 3 个固定阶段。功能
归属必须明确属于某一个生命周期阶段，**不要混淆**。

| ID | 生命周期阶段 | 谁在开 | 执行时大模型会不会逐步读 HTML？ |
|---|---|---|---|
| L1 | 自主学习 | 系统 | 是 —— 仅限学习阶段，有限使用 |
| L2 | 用户引导学习 | 用户（可视化浏览器里） | 否 —— 系统只是记录用户 |
| L3 | 实际工作 | 系统，基于学过的数据 | **否 —— 这是核心不变量** |

下面逐一展开每个生命周期阶段、涉及的 Agent，以及绝不能破坏的不变量。

---

## 4. L1 · 自主学习

**触发**：系统第一次见到一个页面（或用户强制重新学习）。

### 4.1 流水线

顺序执行。每一步有清晰的输入/输出契约，组件可独立替换。

1. **取 HTML → Full AST**（服务端，`lxml`）。
   DOM 忠实转录；**不做语义改写**。
2. **Full AST → Simplified AST**（结构保留的投影）。
   Simplified AST 去噪但保留节点边界和兄弟顺序。它**不是**
   "页面摘要"。
3. **Agent A · Page Intent Agent / 页面意图 Agent** 读 Simplified AST + 截图，写下
   这个页面是干什么的。
   - 输出：简短的页面用途描述，与 page signature 一起持久化。
   - 这是语义理解，不是可操作元素的抽取。
4. **代码**（纯确定性，无大模型）从页面提取可操作元素：
   fillable / submit / clickable / navigation / select / toggle。
   纯结构分类。
5. **代码**用 Playwright 尝试各种操作，并**把失败也记下来**。
   失败路径作为负面知识保留，不丢弃。
6. **Agent B · Attempt Evaluator Agent / 尝试评估 Agent** 判定每次尝试的结果，标记异常。
   - 输出：单次尝试的 verdict + summary。和 Agent A 独立。
7. **Agent C · Learning Reporter Agent / 学习报告 Agent**（表现层，低优先级）把整个学习过程
   整理成给用户看的报告。
   - 输出：用户可读的报告（这个页面是什么、系统能干什么、有
     什么没搞定）。
   - **不是学习闭环的前置条件**。只要步骤 1–6 + 8 跑通，闭环就
     成立；C 是在那份数据之上加的 UX 打磨。**优先打磨 A / B /
     第 4 / 第 5 步的准确度**，别先投资 C。
8. **持久化**成一条学习过的页面记录：
   - page signature
   - 页面用途（来自 Agent A）
   - 可操作元素（来自第 4 步）
   - 成功路径（来自第 5 步，verdict=success）
   - 失败路径（来自第 5 步，verdict≠success）—— 作为负面知识
     保留，避免重复犯错。

### 4.2 L1 刻意不是

- 不是 skill 注册表。学过的记录是一条按 page signature 归档的
  数据 blob，不是具名 skill。
- 不是一个大一统 Agent。Agent A / B / C 是**分开的**：不同 prompt、
  不同输出、不同失效模式。**不要合并**。
- 不是永久结论。支持重新学习。页面变了或用户纠正了，都可以重学。

---

## 5. L2 · 用户引导学习

**触发**（任一）：

- 用户主动进入引导学习模式（给系统已经部分掌握的页面补数据）。
- 用户在 L3 执行过程中**接管**（错误恢复或主动交接）。接管
  自动进入引导学习 —— 从那一刻起系统记录用户的所有操作。

L2 分成两个子模式。

### 5.1 User Demonstration / 用户演示记录

1. 系统在**可视化**（非 headless）Playwright 浏览器里打开页面 ——
   用户在开。
2. 用户正常操作。
3. 系统记录每次交互：
   - 用了哪个 selector（从真实事件 target 反解）
   - 输入了什么 / 点了什么
   - 交互后可观测的状态变化
4. 记录的操作追加到页面的学习记录里，标 `provenance = user`。
   这些操作和 L1 路径一起参与 L3 的路径规划。

### 5.2 Guided Teaching / 引导式教学

引导式教学仍然是 L2：用户执行真实浏览器动作，系统记录用户实际做了
什么。

1. 系统在可视化 Playwright 浏览器里打开页面。
2. Agent H · Teaching Guide Agent / 教学引导 Agent 和用户沟通下一步建议。
3. UI 可以给目标元素加高亮、阴影、指示器、tooltip 或下一步提示。
4. 用户点击、输入、选择或以其他方式操作页面。
5. 系统记录真实事件 target、value 和可观测状态变化。
6. 只有记录到的用户动作才能追加到学习记录，并标记为
   `provenance = user`。

Agent H 的建议是引导，不是证据。除非用户实际执行了该动作，否则不能
把建议写成 LearnedPath action。

### 5.3 不变量

L2 记录的是**用户真实操作**。
- **不**用大模型去推测用户意图。
- **不**事后改写用户做了什么。
- Provenance 永远保留，方便以后审查时信任数据来源。

---

## 6. L3 · 实际工作

这才是终端用户关心的生命周期阶段。L1 和 L2 存在的唯一目的，是让
L3 **便宜、快、可靠**。

**触发**：用户提需求（例如"登录 X 下载本周报表并保存为 CSV"）。

### 6.1 运行形态 —— 快乐路径不是全部

真实的 L3 运行**不是**一条从规划到报告的直线。一旦页面跟学习
记录预期不符，运行会在多个分支之间切换：

```
规划 (D) → 执行 → 观察 → 成功？ ─── 是 ──→ 报告 (E)
                         │
                         └── 否 ──→ 恢复对话 (F)
                                     ├── 重新规划  ──→ 回到执行
                                     ├── 从头重跑  ──→ 回到规划
                                     └── 交给用户  ──→ 进入 L2
```

会把运行切出快乐路径的触发条件：

- 动作报错（超时、找不到元素、5xx）
- 可观测状态没有按学习路径预期的方式变化
- 页面漂移（元素移位、selector 失效、布局变化）
- 用户中断（§6.9）

下面几节分别讲每条支路。**"快乐路径"只是晴天子集**；错误 / 漂移 /
接管都是一等公民，不是异常情况。

### 6.2 快乐路径

1. **Agent D · Path Planner Agent / 路径规划 Agent** 读取：
   - 用户的任务描述
   - 目标页面的学习记录

   然后**选一条路线**。路线是一串具体动作（selector + 动作类型 +
   值），从学过的路径里选出来。

   Agent D **绝不读原始 HTML**。它只读学过的数据。它的工作是
   "从已验证的路径里挑正确那条"，**不是**"从零开始想要点哪里"。

2. **代码**用 Playwright 执行所选路线。
   - Selector / 值 / 动作类型完全确定 —— 来自学习数据，不是
     大模型在循环里做的决定。
   - 每个动作的观测（URL 前后、DOM 信号等）记录下来给报告 Agent。

3. **Agent E · Result Reporter Agent / 结果报告 Agent** 把结果总结给用户。
   输出：自然语言结果 + UI 可渲染的结构化字段。

### 6.3 任务结果验证

L3 不只是“路径执行完了”。它还必须判断用户任务的 postconditions 是否
成立。

Agent E 不能只根据执行日志干净就脑补成功。它应基于执行结果、
postcondition check、artifact 状态、可见错误，以及可用的 rule / spec
信号来汇报。如果 WebAgentFlow 无法验证结果，必须向用户明确报告
`uncertain` / `needs review`，而不是宣称完成。

Postconditions 可以来自选定的 LearnedPath、Agent D 的任务计划、用户
显式确认，或 rule / spec 信号。例如：

- final URL 或路由
- DOM 文本或可见状态
- row count 或筛选结果数量
- 下载 artifact 存在
- 最终页面状态
- 可见错误或警告

### 6.4 核心不变量

L3 执行过程中，**大模型只在边界处介入** —— 开始时规划，
结束时报告，恢复 / 中断对话，或用户教学 / 接管边界。
它**绝不**被调用来决定下一次点击、下一次按键、填哪个字段，因为
这些决定已经编码在学习记录里。

**这一条不可商量**。这就是 WebAgentFlow 跟"大模型盯着浏览器乱点"
的根本区别。破坏这一条，你就做的是另一个产品了。

### 6.5 Action Risk & Consent Gate / 操作风险与确认门

规划不确定时，执行前需要确认。有些操作即使 planner 很确定，也仍然
需要确认：危险或不可逆操作、对外发送、删除、类似付款的流程、权限
修改、批量修改，或任何用户自定义的敏感操作。

第一版应使用 deterministic policy gate 加 user-configurable rules。
Conversation Orchestrator 在执行前插入这个 consent gate。未来可以扩展
成 Risk / Consent Advisor，但本文不为此新增正式 Agent。

### 6.6 Artifact 生命周期

真实任务经常产生或消费 artifact：下载文件、截图、生成的证据、导出的
CSV / PDF / Excel 文件、上传文件，或最终任务结果附件。

WebAgentFlow 最终需要 artifact 生命周期：

- capture
- storage
- display / return 给用户
- retention
- cleanup

这是未来路线图能力，不要求 M10.2 replay / drift 实现。

### 6.7 Multi-Page / Multi-Path Workflow

终局任务可能需要跨一个或多个页面组合多个 LearnedPath。Agent D 未来
可以把多条已学路径组合成 workflow，但不能在运行时从 raw HTML 凭空
发明路径。

Multi-page workflow composition 是后续能力。M11 MVP 不需要完整覆盖
所有 workflow 场景。

### 6.8 错误处理

动作失败时（页面报错、找不到元素、可观测状态没变化、5xx 等等）：

1. 执行**暂停**。**绝不**偷偷重试。
2. **Agent F · Recovery Dialogue Agent / 恢复对话 Agent** 开一个和用户的对话：
   - 发生了什么
   - 哪一步失败了
   - 系统认为有哪些选项
3. 基于用户回复，系统三选一：
   - **重新规划继续**：Agent D 根据新上下文重新选一条路线，继续。
   - **从头重跑**：用于部分状态不安全时。
   - **交给用户**：进入 L2。用户手动完成任务，动作被记录、
     反哺学习记录。

### 6.9 用户主动中断

用户可以随时停止运行。停下时：

1. 执行立刻暂停。
2. **Agent G · Abort Dialogue Agent / 中断对话 Agent** 开对话：
   - 目前做了什么
   - 页面处于什么状态
   - 用户想怎么办（继续 / 重跑 / 交接 / 放弃）
3. 系统按用户回复执行。

中断和错误**不是一回事**：中断是用户在一次原本正常的运行上主动
介入。不同 Agent、不同 prompt、不同语气。

---

## 7. Agent 总表（单一权威）

这些是**独立**的 Agent。不要合并。不同 prompt、不同输入、不同输出、
未来会用不同的模型。

| ID | 名称 | 生命周期阶段 | 读什么 | 产出什么 |
|---|---|---|---|---|
| A | Page Intent Agent / 页面意图 Agent | L1 | Simplified AST + 截图 | 页面用途描述 |
| B | Attempt Evaluator Agent / 尝试评估 Agent | L1 | 尝试日志 + 前后状态 | 单次尝试的 verdict + 异常 |
| C | Learning Reporter Agent / 学习报告 Agent*（低优先、表现层）* | L1 | 整个学习过程 | 给用户看的学习报告 |
| D | Path Planner Agent / 路径规划 Agent | L3 | 用户任务 + 学习记录 | 选定的具体路线 |
| E | Result Reporter Agent / 结果报告 Agent | L3 | 执行结果 | 给用户看的结果 |
| F | Recovery Dialogue Agent / 恢复对话 Agent | L3（错误） | 错误上下文 + 近期步骤 | 对话记录 + 下一步动作 |
| G | Abort Dialogue Agent / 中断对话 Agent | L3（用户中断） | 当前状态 + 中断信号 | 对话记录 + 下一步动作 |
| H | Teaching Guide Agent / 教学引导 Agent | L2 | teaching goal + 当前页面分析 + 已知 LearnedPath + 近期用户动作日志 + 可选失败 / 恢复上下文 | 自然语言指令 + highlight target + 预期用户动作 + 澄清问题 |

Agent H 边界：

- 不 click / fill / 操作浏览器。
- 不伪造用户动作。
- 引导内容和记录下来的 `provenance = user` 动作是两回事。

加新能力时先问：**这属于哪个 Agent？** 如果答案是"新的一个"，那
是产品级决策，**先更新本文档**再写代码。

---

## 8. 跨生命周期阶段不变量

跨所有生命周期阶段都适用。违反就是产品 bug，不是实现细节。

1. **L3 执行过程中，大模型永远不在逐步循环里。** 只在规划 /
   报告 / 对话三处出现。
2. **失败是数据。** 这不只是说 `exploration_runs` 存在。Failed
   attempts、replay drift、`target_missing`、`unsupported_action` 和
   user corrections 未来都应该沉淀成 failure evidence / negative
   knowledge。Planner、learning quality、evaluation 和 optimization
   都可以消费这些负面知识。M10.2 不需要一次性实现全部。
3. **Provenance 永远保留。** 每个学过的动作都知道自己来自 L1
   （系统）还是 L2（用户）。
4. **允许重新学习。** 页面漂移了可以重学，系统不能假定学到的东西
   永久有效。
5. **绝不偷偷重试。** 错误触发对话，不触发隐藏的重试循环。
6. **学习路径和执行路径是两条代码路径。** 用 L1 的编排器去跑
   L3 的任务是坏味道；L3 应该是**无聊的、确定的**。
7. **会话编排归代码所有。** Session state、consent gate、recovery
   routing、abort handling 和 teaching-mode switch 由 Conversation
   Orchestrator 控制，不交给不受约束的 LLM 循环。
8. **引擎卫生很重要。** 对话、日志、截图、artifact 和 LLM prompt
   payload 未来都需要在运行实例内设计 retention、deletion、redaction
   和 audit。这是 engine hygiene，不是 user-account 或 data-governance
   system。

---

## 9. 当前代码库所处位置

诚实对照，让"愿景 vs 现实"的差距显性化。生命周期阶段或交付里程碑落地了就更新这段。

- **L1 步骤 1–2（HTML → AST → Simplified AST）**：服务端解析
  已交付（`html_ast_parser.py` + `ast_simplifier.py`）。自主探索
  当前用的是实时页面分析器（`page_analyzer.py`），不是离线 AST
  管线。两条路径的统一是待做项。
- **L1 步骤 3（Page Intent Agent / 页面意图 Agent）**：**尚未**单独做成一个
  Agent。今天的 Supervisor 把"理解意图"和"评估结果"混在一起了。
- **L1 步骤 4–5（元素抽取 + 尝试）**：已交付（在自主探索
  子系统里）。
- **L1 步骤 6–8（评估 + 报告 + 持久化）**：部分完成。verdict +
  5 项验证评分卡 + Supervisor 总结都有了，但这些都是**探索阶段的
  产物**。**面向最终产品的用户可读学习报告仍在探索形态** —— 当前
  的输出更像开发者调试面板，不是 Agent C 应该最终产出的东西。
  **"落成学习路径"在交付里程碑 M10.1 已交付** —— `pass_gate
  = pass` 的运行自动写入 `learned_paths`，主键为
  (page_template, query_signature, dom_fingerprint, scenario)，并
  携带 trust 生命周期（`provisional` / `confirmed` / `flaky` /
  `deprecated`），由操作者在 run 详情页推动状态变化。基于学过路径
  的 replay / drift detection 正在 M10.2 中规划。
- **L2（用户引导学习）**：未开工。2026-04-20 清理把旧的
  Chrome 扩展移除了；L2 会从零开始基于**可视化** Playwright
  浏览器（见 §5.1）搭建，不再依赖扩展。User Demonstration、Guided
  Teaching 和 Agent H 当前都尚未实现。
- **L3（实际工作）**：未开工。没有 Path Planner Agent / 路径规划
  Agent，没有 task-to-path 执行闭环，没有 runtime conversation
  surface，没有 Conversation Orchestrator，没有结果验证闭环，也没有
  恢复对话。Replay / drift 是 M10 基础；M11 是运行时沟通基础，M11.1
  是第一版 L3 快乐路径 MVP。

某个生命周期阶段完整落地后，回来更新本段。

### 9.1 交付里程碑对齐

当前交付计划刻意把“路径资产”与“真实任务执行”拆开：

| 里程碑 | 产品作用 | 产品内部 Agent |
|---|---|---|
| M10 · Path Asset Foundation / 路径资产基础 | 让 LearnedPath 可复用：持久化、目录、replay、drift detection。 | 不新增 Agent；提供执行底座。 |
| M11.0 · Runtime Conversation Shell & Orchestration / 运行时沟通与编排 | CLI-first 运行时沟通入口、Conversation Orchestrator、session state、用户消息、engine events、confirmation、pause、resume、abort、takeover 和 teaching-mode routing。 | 默认不新增 Agent；随能力落地路由到 Agent D / E / F / G / H。 |
| M11.1 · Task-to-Path Planning & Execution MVP / 任务到路径规划与执行 MVP | 第一版 L3 快乐路径：用户任务 → 选择 / 绑定 LearnedPath → consent gate → 执行 → 验证 → 汇报。 | Agent D · Path Planner Agent；Agent E · Result Reporter Agent。 |
| M12 · Recovery & Handoff / 恢复与接管 | L3 失败和中断分支：暂停、解释、重新规划、重跑或交给用户。 | Agent F · Recovery Dialogue Agent；Agent G · Abort Dialogue Agent。 |
| M13 · User-Guided Learning & Teaching / 用户引导学习与教学 | L2 可视化浏览器接管、用户演示、引导式教学、路径纠正 / provenance 写回。 | Agent H · Teaching Guide Agent；保留用户来源。 |
| M14 · Learning Quality Agents & Negative Knowledge / 学习质量与负面知识 | 回到 L1 质量：页面用途、简单尝试评估、学习报告、更丰富控件和 pattern，以及 failure evidence。 | Agent A · Page Intent Agent；Agent B · Attempt Evaluator Agent；Agent C · Learning Reporter Agent。 |
| M15 · Automated Evaluation & Continuous Optimization / 自动评估与持续优化 | 回归运行、漂移告警、质量趋势。 | 复用 Agent B / Supervisor 式评估；默认不新增 Agent。 |
| M16 · External Interfaces / 对外接口 | 在运行时主链路可用后，稳定 API / CLI / Skill / Tool，供外部调度者调用。 | 不新增产品 Agent；暴露既有能力。 |
| M17 · Multi-Page Workflow Composition / 多页工作流组合 | 把多个 LearnedPath 组合成更大的 workflow，但不从 raw HTML 凭空发明路径。 | 扩展 Agent D 的规划输入；默认不新增 Agent。 |
| M18 · CLI Distribution & Integration Readiness / CLI 分发与集成就绪 | 稳定 CLI 分发、local packaging、API / CLI examples、scripting / batch usage、integration cookbook，以及版本化 CLI / API contract。 | 默认不新增产品 Agent。 |

M10.2 replay 在这次重排后仍然有价值：它是 LearnedPath 数据的第一个
确定性消费者。它**不**实现 Agent D，也**不**实现 L3 任务规划；它给
M11.1 提供一个可安全调用的执行底座。

---

## 10. 开源交付形态

WebAgentFlow 不只是一个带界面的应用，也应当作为一个**可独立运行、
可被外部调度的开源工具**存在。本节讲的是**引擎能力如何对外开放**，
不是一个新的生命周期阶段。

### 10.1 两种交付形态

WebAgentFlow 至少支持两种使用形态：

1. **完整应用**
   - 用户直接使用 WebAgentFlow 自己的界面。
   - 在可视化环境中进行学习、运行、复核、接管。
   - 这是面向最终用户的主形态。

2. **能力开放形态**
   - 将学习、规划、执行、验证等能力，以稳定接口对外暴露。
   - 外部系统或第三方 Agent 可以调用这些能力。
   - 这类调用方包括但不限于：Codex、Claude Code、OpenClaw，或其他
     Agent / 自动化系统。

### 10.2 对外暴露的能力范围

对外开放的不是"整个产品页面"，而是若干明确的**能力单元**。至少包括：

- **页面学习**
  - 对页面做结构分析。
  - 抽取可操作元素。
  - 产出页面理解、尝试结果、学习报告。
- **路径规划**
  - 基于已有学习数据，为具体任务**选择 / 组合 / 补全**可执行路径。
    **绝不**在运行时让大模型现编一条新路径。
- **执行**
  - 在真实浏览器中自动完成网页操作。
  - 返回逐步执行日志、可观测状态变化、结果状态。
- **验证**
  - 对执行结果进行规则验证 / spec 对照 / 项目内 Agent 复核。
- **用户引导学习记录**
  - 在用户接管时记录用户真实操作，补充学习数据。

### 10.3 对外接口形态

以上能力应当至少支持以下三类对外入口：

1. **API**
   - 供其他系统通过 HTTP / streaming 方式调用。
   - 机器到机器的标准入口。
2. **CLI**
   - 供运行时沟通入口使用，也供开发者直接在终端中调用某项能力。
   - 适合第一版 CLI-first 产品闭环、调试、批处理、脚本，或集成到
     自建操作台。
3. **Skill / Tool 形态**
   - 供第三方 Agent 框架把 WebAgentFlow 当作一个"可调用工具"。
   - 外部 Agent 负责决定"什么时候调用"。
   - WebAgentFlow 负责真正执行浏览器相关能力。

### 10.4 主体关系

即使存在 CLI / Skill / API，主体关系也不变：

- **WebAgentFlow** 是网页学习与执行内核。
- **外部 Agent** 是调度者，它决定调什么、什么时候调，但**不直接
  逐步操作网页**。
- **用户** 是最终确认者，且可以在任何时候接管 —— 接管即进入
  L2 用户引导学习。

第三方 Agent 可以调用 WebAgentFlow，但**不应替代 WebAgentFlow 去
直接实现浏览器逐步执行逻辑**。

> **澄清 —— 本文周围会出现三种"Agent"，不要混在一起**：
>
> 1. **产品内部 A–H Agent**（§7）—— 运行时跑在 WebAgentFlow **内部**
>    的角色（页面意图、规划、恢复对话…）。由本文定义。
> 2. **第三方 Agent**（本 §10）—— 运行时的**外部调度者**，通过
>    WebAgentFlow 的 CLI / Skill / API 来让浏览器干活。不是
>    WebAgentFlow 的一部分。
> 3. **AI 编码 Agent**（Claude Code、Codex 等）—— **开发阶段**操作本
>    仓库的工具。**完全不在运行时链路里**。无论 §10 有没有 CLI /
>    Skill 入口，都受 `CLAUDE.zh.md` §"AI 编码 Agent —— 执行边界"
>    硬约束。

### 10.5 开放能力的边界

对外开放能力**不会放宽**现有不变量：

- L3 实际工作中，大模型不进入逐步执行循环。
- 执行依旧由代码和浏览器自动化完成。
- 失败、接管、恢复对话等仍然遵守 L1/L2/L3 生命周期模型。
- 对外接口只是"调用方式不同"，**不是产品逻辑改变**。

### 10.6 当前状态与优先级

本节描述的是**长期交付形态**，不代表当前已经全部完成。§2.1 的
CLI-first 运行时沟通入口可以更早出现，因为它是跑通核心产品闭环的一部分。
M16 则是之后对外部调度接口和更广义 tooling contract 的稳定化。

当前代码库已经具备部分基础：

- 浏览器执行与探索能力。
- 页面分析 / 动作规划 / 验证能力。
- autonomous workbench 作为人工触发与观察入口。

后续需要逐步补齐：

- 运行时 CLI 沟通入口。
- 更稳定的外部 CLI 入口。
- 更清晰的 Skill / Tool 接口定义。
- 面向第三方 Agent 的调用约定。
- 面向外部调用的能力边界与输入输出协议。

### 10.7 实例本地数据

引擎的数据边界是**一份运行中的实例**。WebAgentFlow 只在该实例内
持久化引擎产物：LearnedPath、信用记录、反馈历史。

"真实用户数据微调"不是另一套机制，它就是 L1/L2/L3 生命周期模型在**这个实例**
的页面上持续发生：用户在 L2 演示、在 L3 复核时确认或
驳回，引擎的 LearnedPath 存档随之调整。**一个实例被使用得越多，信号
越丰富，对这个用户的真实页面适应得越好** —— 这些数据不离开本实例。

Session 过期、跳转、权限拒绝或授权缺失，都是运行时恢复 / 用户沟通
事件。

引擎还需要对对话、日志、截图、artifact 和 LLM prompt payload 做基础
卫生设计：记录什么、保留多久、如何删除、什么可以脱敏、什么可以审计。
这是运行实例内的 engine hygiene，不是项目自有身份层或托管数据治理系统。

不变量：

- 引擎**不得**把"实例身份"塞进 LLM prompt、日志、SSE 事件、对外上报
  里。
- 引擎**不得**自己把学到的数据向实例外推送。
- 持久化代码**应当**保持普通 repo 边界，不加入推测性的 ownership
  或存储抽象。

这套表述在交付里程碑 M10 随 LearnedPath 持久化一同显式化。在此之前
"一份实例 = 一个人的数据"是隐式约定。

---

## 11. 相关文档

- [`architecture.zh.md`](./architecture.zh.md) —— 代码怎么组织
  （分层、AST 双轨、services 子包）。和本文互补，不替代。
- [`roadmap.zh.md`](./roadmap.zh.md) —— 运营视角：已交付 / 在做 /
  下一步。
- [`scope-boundaries.zh.md`](./scope-boundaries.zh.md) —— **当前
  刻意不做**的事。
- [`product-model.md`](./product-model.md) —— 英文原版。

---

开源交付形态描述的是 WebAgentFlow 的"能力开放方式"，不是新的产品
生命周期阶段；它建立在 L1/L2/L3 生命周期模型之上。

---

本文为 [`product-model.md`](./product-model.md) 的中文镜像，内容以
英文版为准。
