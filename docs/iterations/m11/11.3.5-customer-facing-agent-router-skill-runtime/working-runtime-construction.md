# WebAgentFlow M11 Working Runtime 施工稿 v6

版本：M11 working build / v0.1 本地代码对齐稿  
父迭代：11.3.5 · Customer-Facing Agent Router & Skill Runtime  
定位：总设计和施工包边界，不替代后续 11.3.5.3+ 的完整迭代文档。

目标：做出一个真的可以工作的 WebAgentFlow，不只是完成固定值 replay，
也不只是完成 Agent 编排图。施工方式是先打通一条可验收的窄闭环，再逐步加入
多候选、状态账本、失败恢复和更复杂规划。

## 0. 本版结论

本稿把 working runtime 的第一条闭环收敛到一个核心事实：

```text
学习新增项目 A -> 执行新增项目 B
```

这不是普通 replay。系统必须在学习阶段识别出 `record_name` 是可替换参数，并在执行阶段
把用户新输入的 `测试项目B` 替换进 replay action。否则系统只是重复录制值
`测试项目A`，不能算学会“新增项目”这个操作。

当前本地代码事实：

| 事实 | 当前状态 | 本地路径 |
|---|---|---|
| `apps/fixture-site` 没有 `/records` 路由 | `/target-login`、`/workspace-home` 已有，`/records` 需要新增 | `apps/fixture-site/src/router/index.ts` |
| `ReplayRequest` 只有 `url` | 没有 `slot_overrides` / `evidence_targets` | `apps/api/app/schemas/learned_path_replay.py` |
| `ReplayAction` 有固定 `value` | 没有 `value_slot` | `apps/api/app/schemas/learned_path_replay.py` |
| `run_replay()` 以 `learned_path + url` 为核心输入 | runtime 在 `finally` 中 stop，DOM evidence 要在 stop 前采集 | `apps/api/app/services/learning/learned_path_replay.py` |
| `TaskResultReporter` 已存在 | outcome 是 `verified / failed / uncertain / needs_review / blocked`，且保守处理无 postcondition evidence 的情况 | `apps/api/app/services/task_planning/result_reporter.py` |
| conversation runtime pieces 已存在 | 包括 `chat_runtime.py`、`entry_gate.py`、`intake.py`、`router_agent.py`、`skills.py`、`page_understanding.py`、`state.py` | `apps/api/app/services/conversation/` |
| task planning services 已存在 | 包括 `planner.py`、`preview.py`、`result_reporter.py`、`retrieval.py` | `apps/api/app/services/task_planning/` |
| `_fill_values_from_intake()` 只处理账号密码 | 当前不提取 `record_name` | `apps/api/app/services/conversation/chat_runtime.py` |

## 1. 核心目标

### 1.1 最终目标

WebAgentFlow 当前阶段的目标不是让 Agent 图看起来完整，而是稳定完成：

```text
用户自然语言输入
  -> 系统理解目标
  -> 缺信息时会追问
  -> 信息完整时能学习页面操作
  -> 学习完成后形成可复用、可参数化的 LearnedPath
  -> 用户再次提出新的执行参数
  -> 系统找到已学路径
  -> replay 时替换运行时参数
  -> 页面产生可观察结果
  -> 系统基于 evidence 保守报告结果
```

### 1.2 第一条真实闭环

P0 第一闭环必须是：

```text
新增 fixture-site /records 列表页
  -> 用户：学习新增项目，名称叫测试项目A
  -> 系统学习新增项目操作
  -> LearnedPath 中 fill action 绑定 value_slot=record_name
  -> 用户：帮我新增项目，名称叫测试项目B
  -> 系统用 slot_overrides.record_name=测试项目B 执行 replay
  -> 页面列表出现测试项目B
  -> runtime 关闭前采集 ExecutionEvidence
  -> TaskResultReporter 输出 verified / uncertain / failed / needs_review / blocked
  -> 系统给出保守回复
```

关键点：

```text
学习 A 后执行 B，必须真的填入 B。
不能 replay 固定录制值 A。
```

## 2. 架构原则

### 2.1 一句话原则

WebAgentFlow M11 的 chat runtime 采用 code-owned Orchestrator + LLM semantic
agents + controlled application skills。LLM 负责理解和建议；代码负责状态、
边界、确认、技能调用、参数替换、证据采集、结果验证和最终裁决。

### 2.2 正确架构

```text
Code-owned Orchestrator / Runtime
  + LLM semantic agents
  + controlled application skills
  + explicit runtime metadata
  + parameterized replay
  + evidence-based result reporting
```

### 2.3 错误架构

```text
Router Agent 直接执行浏览器动作
Learning Agent 私自转交 Execution Agent
Execution Agent 查不到路径后私自调用 Learning Agent
Page Understanding Agent 顺手启动学习
Response Agent 自己决定业务状态
Replay 固定使用录制值，忽略用户新的运行时参数
Reporter 没有 evidence 也说成功
```

## 3. 当前现状 vs 新增能力

### 3.1 当前已有能力

| 能力 | 当前状态 | 说明 |
|---|---:|---|
| Conversation runtime pieces | 已有 | `chat_runtime.py`、`entry_gate.py`、`intake.py`、`router_agent.py`、`skills.py`、`page_understanding.py`、`state.py` 等已存在 |
| Entry Gate | 已有 | 处理问候、能力询问、非网页任务、是否进入 heavy runtime |
| Intake Agent | 已有 | 负责用户语义理解 |
| Context Collector | 已有 | 收集 pending、learned actions、历史消息等上下文 |
| Customer-Facing Agent Router | 已有 | 推荐下一步 agent / skill，不直接执行 |
| Page Understanding pieces | 已有 | 可作为页面理解服务边界 |
| Learning path replay | 已有 | 但当前 replay 是固定 action value，不支持 runtime slot override |
| TaskPathPlanner | 已有 L3 deterministic service | 不进入 P0 单路径 happy path |
| TaskResultReporter | 已有 L3 deterministic service | 需要适配新的 ExecutionEvidence 输入 |
| `pending_intake` | 已有 | 缺学习字段时可追问和续接 |
| `pending_target` | 已有 | 用户只给 URL 时可保存目标 |
| `last_no_path_reason` | 已有 | 未找到路径时记录原因 |
| `learned_actions` | 已有 | 学习完成后可写入摘要 |

### 3.2 P0 必做缺口

| 缺口 | 是否 P0 必做 | 原因 |
|---|---:|---|
| `/records` 列表测试页 | 是 | 当前没有稳定列表页闭环 |
| `record_name` slot extraction | 是 | 没有它无法表达“新增 B” |
| `_fill_values_from_intake()` 支持 `record_name` | 是 | 学习和执行都需要把用户 slot 变成 runtime fill values |
| LearnedPath action 参数绑定 | 是 | 学习 A 后必须知道哪个 fill action 可替换 |
| `ReplayRequest.slot_overrides` | 是 | 执行 B 时需要把 B 传给 replay |
| `ReplayAction.value_slot` | 是 | action 需要知道哪个 slot 替换哪个 value |
| `run_replay()` 应用 slot override | 是 | replay 必须实际填入 B |
| runtime 关闭前采集 DOM evidence | 是 | runtime stop 后就拿不到页面 DOM |
| Reporter adapter | 是 | 当前 reporter 不直接消费新的 `ExecutionEvidence[]` |
| Reporter 保守状态映射 | 是 | 必须贴合 `verified / failed / uncertain / needs_review / blocked` |

### 3.3 不进 P0 的缺口

| 缺口 | 优先级 | 说明 |
|---|---:|---|
| `pending_choice` | P1 | 多候选、低置信、混乱输入时使用 |
| `active_task` / 最小 RuntimeLedger | P1/P2 | 统一运行态账本，P0 不大重构 |
| TaskPathPlanner 接入 chat | P2 | 多候选 / planning preview / 复杂目标时接入 |
| 基础 Failure Recovery | P2 | 先做重试 / 重新学习 / 取消 |
| Teaching Guide Agent | P3 | 后续 guided teaching |
| `learn_then_execute` 自动组合 | P3 | 当前继续保守阻断 |

## 4. 施工分包

### 4.1 包 0：文档同步包

目标：让文档和当前代码状态对齐，防止后续实现被旧计划带偏。

| 任务 | 优先级 | 说明 |
|---|---:|---|
| 同步 docs / roadmap / M11 plan | P0 | 标清 11.3.5 已有 runtime pieces |
| 标注 Orchestrator / Runtime 是 code-owned | P0 | 不能施工成自由 LLM Agent |
| 标注 Router 只能建议 | P0 | 不能调用 skill，不能输出执行细节 |
| 标注 TaskPathPlanner 已实现但不进 P0 | P0 | 防止简单单路径也绕 planner |
| 标注 TaskResultReporter 已实现但需要 adapter | P0 | 不能假设它直接消费 `ExecutionEvidence[]` |
| 标注 `/records` 是新增测试页 | P0 | 当前 fixture-site 没有该路由 |
| 标注 `pending_choice` / `active_task` 是新增能力 | P0 | 不能误写成当前行为 |

### 4.2 包 1：`/records` 参数化新增闭环包

这是当前第一施工包。

范围只做：

```text
新增 /records
  -> record_name slot extraction
  -> 学习新增项目 A
  -> LearnedPath action value_slot 参数绑定
  -> 执行新增项目 B
  -> ReplayRequest.slot_overrides
  -> run_replay 应用 slot override
  -> replay 后、runtime stop 前采集 ExecutionEvidence
  -> Reporter adapter
  -> TaskResultReporter 保守回复
```

包 1 不做：

```text
pending_choice
active_task 完整账本
TaskPathPlanner chat 接入
搜索 / 编辑 / 删除全量闭环
复杂 Failure Recovery
learn_then_execute
```

### 4.3 包 2：`pending_choice` / 最小 ledger 包

范围：

```text
pending_choice
choice_id 私有映射
最小 active_task contract
pending 清理 / 过期
cancel 清理
```

### 4.4 包 3：基础失败恢复包

范围：

```text
执行失败 -> 保守报告
找不到元素 -> 建议重新学习
URL 不匹配 -> 重新确认
成功证据不足 -> 请求用户确认 / 重新检查
提供 A. 重试 B. 重新学习 C. 取消
```

### 4.5 包 4：TaskPathPlanner chat 接入包

范围：

```text
多个 learned actions
用户目标模糊
planning preview / confirmed execution path
TaskPathPlanner 生成候选
pending_choice 展示 A/B/C
Orchestrator 内部解析 choice_id
```

## 5. 当前主链

### 5.1 `wagent chat` 当前主链

```text
用户消息
  |
  v
Conversation Orchestrator / Dispatcher
code-owned 外层控制器
  |
  v
Interactive Chat Runtime
code-owned 编排核心
  |
  v
Conversation Entry Gate
  |
  +-- 不需要 heavy runtime
  |      |
  |      v
  |   Unified Response Writer
  |   直接回复问候 / 能力说明 / 非网页任务引导
  |
  +-- 需要 heavy runtime
         |
         v
      Conversation Intake Agent
      解析 intent / target / action / slots / missing_fields
         |
         v
      collect_conversation_context
      收集 pending_target / pending_intake / learned_actions / no-path reason
         |
         v
      Customer-Facing Agent Router
      推荐 next_agent + recommended_skill
      只建议，不执行
         |
         v
      Runtime Adjudicator
      code-owned 最终裁决
         |
         +-- ask_user_for_missing_info
         |
         +-- inspect_target_page / understand_page
         |
         +-- start_learning
         |
         +-- start_replay
         |
         +-- no-path / guided learning required
```

### 5.2 包 1 目标主链

```text
用户：学习新增项目，名称叫测试项目A
  |
  v
Intake Agent
识别 learn_operation + record_name=测试项目A
  |
  v
Runtime
生成 fill_values.record_name=测试项目A
  |
  v
Learning Agent Boundary
组织 start_learning
  |
  v
Learning Service
生成 LearnedPath actions
  |
  v
Runtime Parameterizer
找到 fill value=测试项目A 的 action
写入 value_slot=record_name
  |
  v
Response
回复学习完成，说明项目名称可替换


用户：帮我新增项目，名称叫测试项目B
  |
  v
Intake Agent
识别 execute_operation + record_name=测试项目B
  |
  v
Runtime
找到唯一“新增项目” learned action
检查 LearnedPath 支持 value_slot=record_name
  |
  v
ReplayRequest
slot_overrides.record_name=测试项目B
evidence_targets.dom_text_present=测试项目B
  |
  v
run_replay
fill action 使用 override 后的 B
  |
  v
Evidence Capture
runtime stop 前检查 DOM 文本
  |
  v
TaskResultReporter Adapter
replay result + evidence -> reporter input
  |
  v
TaskResultReporter
输出 verified / uncertain / failed / needs_review / blocked
  |
  v
Response
保守回复执行结果
```

## 6. Agent / 组件表

| 名称 | 类型 | 当前状态 | 当前定位 | 输入 | 输出 | 可用技能 / 能力 | 不能做什么 | 所属施工包 |
|---|---|---:|---|---|---|---|---|---|
| Conversation Orchestrator / Dispatcher | 代码控制器 | 已有 | 外层总入口、会话状态、命令处理、事件落库、最终结果统一出口 | raw user input、session、command、metadata | DispatchResult、conversation events、最终回复 | 调 Interactive Chat Runtime、处理 cancel / abort / command | 不做自由 LLM 判断，不直接模拟网页操作 | 已有，包 0 文档同步 |
| Interactive Chat Runtime | 代码编排核心 | 已有 | `wagent chat` 主链调度台 | session、message、metadata、runtime context | handler result、skill call、state update、response | Entry Gate、Intake、Context、Router、Learning、Execution | 不把最终控制权交给 Worker Agent | 已有，包 1 扩展 |
| Conversation Entry Gate | 入口组件 | 已有 | 判断是否进入 heavy runtime | raw message、session metadata、pending 状态 | enter runtime / direct response | greeting、capability、unsupported、web task candidate | 不查 learned path，不执行浏览器 | 已有 |
| Conversation Intake Agent | LLM + deterministic fallback | 已有 | 用户语义理解 | raw message、pending context、recent context | intent、target、action、slots、missing_fields、confidence | URL 提取、slot 提取、补充信息识别 | 不决定最终 next_agent，不调用 skill | 已有，包 1 扩展 `record_name` |
| Conversation Context Collector | 代码能力 | 已有 | 收集事实账本 | session、current message、metadata | recent messages、pending、learned_actions、last_no_path_reason | `collect_conversation_context` | 不生成业务决策 | 已有 |
| Customer-Facing Agent Router | LLM + fallback | 已有 | 推荐下一步角色和 skill | raw message、intake、context、skill menu | route decision、next_agent、recommended_skill、reason、confidence | 推荐 ask / inspect / learning / web operation | 不直接执行，不输出 selector、browser action、learned_path_id | 已有 |
| Runtime Adjudicator | 代码逻辑 | 已有 | 最终裁决与技能调用守门员 | intake、context、route decision、page context、learned actions | handler selection、skill call、state update、blocking reason | 调 registered application skills 和 internal adapters | 不把状态写入权交给 LLM | 已有，包 1 扩展参数化 |
| Page Understanding Service / Boundary | runtime service | 已有 pieces | 页面观察和理解 | target URL、page context | page summary、visible controls、supported goals、required slots | `inspect_target_page`、`understand_page` | 不启动学习，不执行 replay，不追问用户 | 已有 |
| Learning Agent Boundary | 角色边界 + prompt | 已有 | 组织学习请求 | target、goal、slots、fill_values、context | learning request、learning result、missing info suggestion | `start_learning` | 不直接转交 Web Operation Agent | 已有，包 1 跑通新增项目 |
| LearnedPath Parameterizer | 代码适配器 | 新增 | 给学习后的 actions 绑定参数槽 | learned_path.actions、fill_values、slot binding rules | parameterized actions、binding report | 写 `value_slot` | 不调用浏览器，不改变业务意图 | 包 1 |
| Web Operation Agent Boundary | 角色边界 + replay 服务 | 已有 | 组织执行请求 | matched learned action、target、goal、slot_overrides | replay request、execution result | `start_replay` | 无 matched action 不执行，不自动学习 | 已有，包 1 扩展 slot override |
| Replay Slot Override Adapter | 代码适配器 | 新增 | 执行前把 runtime slot 替换进 action value | ReplayAction、slot_overrides | effective ReplayAction | `value_slot -> value` 替换 | 不替换无绑定 action | 包 1 |
| Execution Evidence Capture | 代码适配器 | 新增 | replay 后、runtime stop 前采集页面证据 | Playwright page、evidence_targets、slot_overrides | ExecutionEvidence[] | DOM text check、unknown fallback | 不调用 LLM，不在 runtime 关闭后读取页面 | 包 1 |
| Task Result Reporter | deterministic service | 已有 | 基于执行证据生成保守结果报告 | execution_status、execution_payload、replay_summary、confirmed_plan_context | TaskResultReport | outcome 推导、保守用户回复 | 不执行、不重试、不调用 LLM、不读 raw HTML | 包 1 接入 adapter |
| Reporter Adapter | 代码适配器 | 新增 | 把 replay result + ExecutionEvidence 转成 reporter 可消费输入 | ReplayResult、ExecutionEvidence[]、user_goal、learned_action_alias | reporter input / confirmed_plan_context / execution_payload | 状态映射、证据摘要、postcondition evidence 写入 | 不改变 reporter 原生 outcome 语义 | 包 1 |
| Unified WAgent Response Writer | code-owned 回复层 | 已有分散实现 | 统一用户可见回复 | runtime result、reporter result、missing fields、errors | final response | 统一话术、保守解释 | 不改变业务状态 | 包 1 可整理 |
| TaskPathPlanner | deterministic L3 service | 已有 | 多候选 / 复杂路径规划 | user goal、candidate learned paths、context | route plan、候选路径 | planning preview、candidate ranking | 不进入 P0 单路径 happy path | 包 4 |
| Pending Choice Handler | 代码状态处理器 | 新增 | 多候选选择 | choices、choice_id、private mapping | selected action / clarification | A/B/C、choice_id mapping | 不暴露 learned_path_id 给 LLM | 包 2 |
| Active Task / Runtime Ledger | 状态 contract | 新增 | 统一 active task 与 pending 状态 | runtime events、worker result | active_task、pending 状态 | 状态保存、过期、清理 | 不做 LLM 判断 | 包 2/3 |
| Basic Failure Recovery Handler | 代码 + 可选 LLM 文案 | 新增 | 基础失败恢复 | replay failure、evidence missing、URL mismatch | retry / relearn / cancel choices | 基础恢复菜单 | 不做复杂自治探索 | 包 3 |
| Teaching Guide Agent | 未来 Agent | 未实现 | 引导式教学 | 用户教学步骤、页面状态 | teaching instructions | future guided teaching | 当前不施工 | P3 |
| Supervisor Agent | 内部验证 Agent | 已有或已有概念 | L1 autonomous exploration 内部验证 | learning / verify evidence | supervisor verdict | 内部验证 | 不参与 `wagent chat` 路由 | 非 chat 主链 |

## 7. Application Skills 与 Internal Runtime Adapters

### 7.1 Registered Application Skills

Registered Application Skills 是 Router 可见的业务级能力菜单。Router 只能推荐这些
skill，不能直接调用，也不能输出 skill 的内部执行 payload。

| Skill | 当前含义 | Owner / Executor | 可由谁请求 | 是否碰浏览器 | 是否写 LearnedPath | 当前策略 | 包 1 是否使用 |
|---|---|---|---|---:|---:|---|---:|
| `collect_conversation_context` | 收集最近消息、pending、learned actions、no-path context | code | conversation_orchestrator | 否 | 否 | heavy runtime 起点 | 是 |
| `inspect_target_page` | 打开 / 检查目标页面，收集 page context | runtime / code | router / worker | 是 | 否 | 需要理解页面时使用 | 可选 |
| `understand_page` | 根据 page context 生成页面理解结果 | page_understanding_agent | router / learning_agent | 否 | 否 | 页面摘要、控件识别、required slots | 可选 |
| `lookup_learned_actions` | 查询当前 session / target scope 已学操作 | code_repository | router / web_operation_agent | 否 | 否 | 执行前匹配路径 | 是 |
| `ask_user_for_missing_info` | 询问缺失目标、输入、确认 | conversation_orchestrator | router | 否 | 否 | 必须写 pending | 是 |
| `start_learning` | 启动产品级 learning，生成 LearnedPath | learning_service | learning_agent | 是 | 是 | 学习网页操作 | 是 |
| `start_replay` | 执行已有 LearnedPath replay | replay_service | web_operation_agent | 是 | 否 | 执行已学路径 | 是 |
| `learn_then_execute` | 学习后执行组合能力 | skill_runtime | learning / web operation | 是 | 是 | 当前保守阻断 | 否 |
| `record_progress_event` | 记录阶段性进度事件 | code | orchestrator / skill_runtime | 否 | 否 | UI loading、阶段进展 | 可选 |
| `record_agent_trace` | 记录脱敏 Agent / routing / page trace | code | agent_runtime | 否 | 否 | debug、审计、回放 | 是 |

### 7.2 Internal Runtime Adapters

Internal Runtime Adapters 不是 Application Skills。它们不得出现在 Router skill menu，
也不得由 LLM agents 直接请求。只能由 code-owned Runtime / Orchestrator / replay service
在已通过业务级 skill 校验后内部调用。

| Adapter | 当前含义 | Owner / Executor | 输入 | 输出 | 包 1 是否使用 |
|---|---|---|---|---|---:|
| `parameterize_learned_path_actions` | 给 LearnedPath actions 绑定 slot | runtime code adapter | learned_path.actions、fill_values、slot binding rules | parameterized actions、binding report | 是 |
| `apply_replay_slot_overrides` | replay 前替换 action value | replay code adapter | ReplayAction、slot_overrides | effective ReplayAction | 是 |
| `capture_execution_evidence` | replay 后、runtime stop 前采集 DOM 证据 | replay runtime adapter | Playwright page、evidence_targets、slot_overrides | ExecutionEvidence[] | 是 |
| `build_replay_reporter_input` | 把 replay result + evidence 转成 reporter 可消费输入 | reporter adapter | ReplayResult、ExecutionEvidence[]、user_goal、learned_action_alias | execution_payload、replay_summary、confirmed_plan_context | 是 |

## 8. `/records` 列表测试页

### 8.1 新增位置

```text
apps/fixture-site/src/pages/ItemsPage.vue
apps/fixture-site/src/router/index.ts
```

新增路由：

```ts
{
  path: '/records',
  name: 'items',
  component: ItemsPage,
}
```

### 8.2 P0 页面功能

| 功能 | P0 必做 | 说明 |
|---|---:|---|
| 新增项目 | 是 | 第一条 happy path |
| 列表展示 | 是 | 用于 DOM evidence |
| 操作状态提示 | 是 | 可作为辅助 evidence |
| 搜索项目 | 否 | P1 |
| 编辑项目 | 否 | P1 |
| 删除项目 | 否 | P2，涉及高风险确认 |

### 8.3 建议数据结构

```ts
type Item = {
  id: string;
  name: string;
  createdAt: string;
};
```

初始化数据：

```ts
[
  { id: 'item-1', name: '默认项目A', createdAt: '...' },
  { id: 'item-2', name: '默认项目B', createdAt: '...' }
]
```

### 8.4 必须有稳定 `data-testid`

| 元素 | `data-testid` |
|---|---|
| 页面根节点 | `records-page` |
| 项目名称输入框 | `record-name-input` |
| 新增按钮 | `record-create-button` |
| 列表容器 | `record-list` |
| 项目行 | `item-row` |
| 项目名称 | `item-row-name` |
| 操作状态 | `operation-status` |

### 8.5 P0 成功证据

新增项目成功后，至少满足：

```text
列表中出现目标文本
```

P0 第一证据：

```json
{
  "kind": "dom_text_present",
  "target": "测试项目B",
  "selector": "[data-testid='record-list']",
  "status": "verified",
  "confidence": 0.95,
  "summary": "列表中出现了名称为“测试项目B”的项目行。"
}
```

## 9. `record_name` slot extraction

### 9.1 目标

用户说：

```text
学习新增项目，名称叫测试项目A
```

Intake / Runtime 必须得到：

```json
{
  "intent": "learn_operation",
  "action": "新增项目",
  "slots": {
    "record_name": "测试项目A"
  }
}
```

用户说：

```text
帮我新增项目，名称叫测试项目B
```

Intake / Runtime 必须得到：

```json
{
  "intent": "execute_operation",
  "action": "新增项目",
  "slots": {
    "record_name": "测试项目B"
  }
}
```

### 9.2 canonical slot

统一使用：

```text
record_name
```

可以兼容别名，但最终内部 contract 必须归一到 `record_name`。

| 用户说法 | 归一 slot |
|---|---|
| 名称叫测试项目A | `record_name=测试项目A` |
| 项目名是测试项目A | `record_name=测试项目A` |
| 新增测试项目A | `record_name=测试项目A` |
| name 是测试项目A | `record_name=测试项目A` |

### 9.3 `_fill_values_from_intake()` 扩展

P0 必须把 `record_name` 转成 fill values：

```json
{
  "record_name": "测试项目A"
}
```

可选兼容别名：

```json
{
  "record_name": "测试项目A",
  "name": "测试项目A",
  "text": "测试项目A"
}
```

canonical key 仍然是 `record_name`。

## 10. 学习阶段参数绑定

### 10.1 问题

如果学习时用户给的是：

```text
测试项目A
```

Learning 录制出来的 fill action 可能是：

```json
{
  "step": 0,
  "action_type": "fill",
  "target_selector": "[data-testid='record-name-input']",
  "value": "测试项目A"
}
```

如果不绑定参数，执行“新增测试项目B”时，replay 仍会填：

```text
测试项目A
```

这不是可工作的 WebAgentFlow。

### 10.2 P0 最小方案

学习完成后，Runtime 根据本轮 fill values 给 LearnedPath action 加参数绑定。

原始 action：

```json
{
  "step": 0,
  "action_type": "fill",
  "target_selector": "[data-testid='record-name-input']",
  "value": "测试项目A"
}
```

参数化后：

```json
{
  "step": 0,
  "action_type": "fill",
  "target_selector": "[data-testid='record-name-input']",
  "value": "测试项目A",
  "value_slot": "record_name"
}
```

### 10.3 P0 绑定规则

只做最小规则：

```text
如果 action.action_type == "fill"
并且 action.value == fill_values["record_name"]
则 action.value_slot = "record_name"
```

### 10.4 绑定结果

成功：

```json
{
  "parameterization": {
    "status": "bound",
    "slots": ["record_name"]
  }
}
```

失败：

```json
{
  "parameterization": {
    "status": "not_bound",
    "reason": "No fill action matched record_name learning value"
  }
}
```

### 10.5 绑定失败时的用户回复

```text
学习完成了一部分，但我没有可靠识别出“项目名称”对应的输入动作。为了避免之后重复填入固定值，建议你重新学习一次新增项目操作。
```

### 10.6 DB 策略

P0 不新增数据库列。在 LearnedPath actions JSON 里增加 `value_slot` 字段即可。

## 11. Replay slot override

### 11.1 `ReplayRequest` 扩展

当前需要扩展为：

```python
class ReplayRequest(BaseModel):
    url: str
    slot_overrides: dict[str, str] = Field(default_factory=dict)
    evidence_targets: list[ExecutionEvidenceTarget] = Field(default_factory=list)
```

P0 请求示例：

```json
{
  "url": "http://localhost:<fixture-port>/records",
  "slot_overrides": {
    "record_name": "测试项目B"
  },
  "evidence_targets": [
    {
      "kind": "dom_text_present",
      "text": "测试项目B",
      "source_slot": "record_name",
      "selector": "[data-testid='record-list']"
    }
  ]
}
```

`<fixture-port>` 只是 fixture-site 本地示例端口。contract 中必须使用 runtime target URL，
不能在代码里硬编码端口。

### 11.2 `ReplayAction` 扩展

新增：

```python
class ReplayAction(BaseModel):
    step: int
    action_type: str
    target_selector: str | None = None
    target_description: str | None = None
    value: str | None = None
    value_slot: str | None = None
```

`_build_replay_actions()` 必须读取：

```python
value_slot=raw.get("value_slot")
```

### 11.3 `run_replay()` 扩展

目标签名：

```python
def run_replay(
    learned_path: LearnedPath,
    url: str,
    *,
    headless: bool = True,
    slot_overrides: dict[str, str] | None = None,
    evidence_targets: list[ExecutionEvidenceTarget] | None = None,
) -> ReplayResult:
```

也可以把 `slot_overrides` 和 `evidence_targets` 放到 `ReplayRequest` 层，再在 service
内展开。关键是执行前必须能拿到 runtime slot overrides。

### 11.4 Slot Override Propagation Path

P0 必须打通完整传播链，不能只改 schema 或只改 `run_replay()`：

1. Intake Agent 提取 `slots.record_name`。
2. Runtime `_fill_values_from_intake()` 生成 `fill_values.record_name`。
3. execute branch 从 `fill_values` 构造 `slot_overrides.record_name`。
4. `start_replay` skill request 携带 `slot_overrides`。
5. `ReplayRequest` 接收 `slot_overrides`。
6. replay endpoint / service 把 `slot_overrides` 传给 `run_replay()`。
7. `run_replay()` 调 `_build_replay_actions()` 读取 `value_slot`。
8. `run_replay()` 在 `execute_action()` 前应用 `apply_slot_override()`。
9. `execute_action()` 实际收到 `value=测试项目B`。
10. step log / debug trace 能证明使用的是 B，不是 A。

P0 验收必须检查 replay step log 中 fill action 的 effective value 是
`测试项目B`，不是学习阶段录制的 `测试项目A`。

### 11.5 应用 override

```python
def apply_slot_override(
    action: ReplayAction,
    slot_overrides: dict[str, str],
) -> ReplayAction:
    if action.action_type != "fill":
        return action

    if not action.value_slot:
        return action

    if action.value_slot not in slot_overrides:
        return action

    return action.model_copy(
        update={"value": slot_overrides[action.value_slot]}
    )
```

执行时：

```python
effective_action = apply_slot_override(action, slot_overrides)
log = execute_action(effective_action, runtime)

wait_result = wait_for_change_after_action(
    page=runtime.page if runtime else None,
    action=effective_action,
    step_log=log,
)
```

`wait_for_change_after_action()` 必须使用 `effective_action`，不能继续使用原始
action。否则等待策略、日志和诊断仍可能引用学习阶段的旧值。

step log / debug trace 应记录：

```text
value_slot=record_name
override_applied=true
effective_value=测试项目B
```

`effective_value` 明文日志只允许用于 P0 `/records` 的非敏感测试字段。任何
credential / token / secret slot 必须记录为 `<redacted>`；后续涉及密码、token
等敏感字段时，`effective_value` 必须脱敏。

### 11.6 安全规则

| 场景 | P0 处理 |
|---|---|
| action 有 `value_slot=record_name`，请求有 `slot_overrides.record_name` | 使用 override 值 |
| action 有 `value_slot=record_name`，请求缺 `slot_overrides.record_name` | 阻断，提示缺少运行时参数 |
| action 没有 `value_slot`，请求有 `slot_overrides.record_name` | 不替换 |
| 用户要求新增 B，但 path 没有参数绑定 | 阻断，不能执行固定值 replay |
| 多个 fill action 匹配同一 slot | P0 可全部替换，但记录 warning |

### 11.7 无参数绑定时回复

```text
我找到了已学习的“新增项目”路径，但它还不是可参数化路径，不能安全地把项目名替换成“测试项目B”。请重新学习一次新增项目操作。
```

## 12. ExecutionEvidence 新增 / 扩展 contract

### 12.1 定位

`ExecutionEvidence` 是新增 / 扩展证据输入 contract。当前 `TaskResultReporter`
已存在，但不能假设它已经直接消费下面这个结构。包 1 要加 adapter。

### 12.2 捕获时机

必须在：

```text
所有 replay action 执行完成之后
runtime.stop() 之前
ReplayResult 返回之前
```

### 12.3 P0 evidence target

```python
class ExecutionEvidenceTarget(BaseModel):
    kind: Literal["dom_text_present"]
    text: str
    source_slot: str | None = None
    selector: str | None = None
```

P0 的 `/records` evidence target 应优先限定在列表容器内：

```json
{
  "kind": "dom_text_present",
  "text": "测试项目B",
  "source_slot": "record_name",
  "selector": "[data-testid='record-list']"
}
```

查找规则：

```text
优先在 selector 指定区域内查找文本。
selector 缺失时才退化为全页面查找。
采集 dom_text_present evidence 时，ExecutionEvidence.target 必须使用
ExecutionEvidenceTarget.text，确保 Reporter verified 条件可以稳定匹配
slot_overrides.record_name。
```

P0 测试数据的 `record_name` 必须唯一，例如 `测试项目B-${timestamp}`，避免页面其他区域
或历史状态里已有同名文本导致假阳性。

### 12.4 P0 evidence

```python
class ExecutionEvidence(BaseModel):
    kind: Literal["dom_text_present", "unknown"]
    target: str | None = None
    status: Literal["verified", "missing", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
```

### 12.5 示例

成功：

```json
{
  "kind": "dom_text_present",
  "target": "测试项目B",
  "status": "verified",
  "confidence": 0.95,
  "summary": "列表中出现了名称为“测试项目B”的项目行。"
}
```

未找到：

```json
{
  "kind": "dom_text_present",
  "target": "测试项目B",
  "status": "missing",
  "confidence": 0.7,
  "summary": "操作执行后，列表中没有确认看到“测试项目B”。"
}
```

无法检查：

```json
{
  "kind": "unknown",
  "target": "测试项目B",
  "status": "unknown",
  "confidence": 0.0,
  "summary": "操作执行后未能采集页面证据。"
}
```

### 12.6 ReplayResult 扩展

推荐直接扩展：

```python
class ReplayResult(BaseModel):
    ...
    execution_evidence: list[ExecutionEvidence] = Field(default_factory=list)
```

如果暂时不想改 `ReplayResult`，可使用 wrapper：

```python
class ReplayWithEvidenceResult(BaseModel):
    replay_result: ReplayResult
    execution_evidence: list[ExecutionEvidence]
```

P0 更推荐扩展 `ReplayResult`，路径短，adapter 更简单。

## 13. TaskResultReporter 接入

### 13.1 原生 outcome

Reporter 原生 outcome 使用：

```text
verified
failed
uncertain
needs_review
blocked
```

不要把 reporter 原生状态改成：

```text
success
partial_success
failed
unknown
```

如果前端需要 `success / partial_success`，只能在 UI wrapper 层映射。

### 13.2 Reporter adapter 输入

```python
class ReplayReporterAdapterInput(BaseModel):
    user_goal: str
    target_url: str | None = None
    learned_action_alias: str | None = None
    replay_status: str
    drift_status: str | None = None
    replay_warnings: list[str] = Field(default_factory=list)
    execution_evidence: list[ExecutionEvidence] = Field(default_factory=list)
```

### 13.3 Outcome 映射

| Replay / Evidence | Reporter outcome |
|---|---|
| replay succeeded + `dom_text_present` verified | `verified` |
| replay succeeded + no useful evidence | `uncertain` |
| replay failed | `failed` |
| replay drifted / unsupported / candidate missing | `blocked` 或 `needs_review` |
| evidence missing target text | `needs_review` |
| runtime error | `failed` |

### 13.4 Reporter verified path 必须打通

P0 不能只把 `ExecutionEvidence` 塞进 event payload。Reporter Adapter 必须让
`TaskResultReporter._check_postconditions()` 能读取到 structured postcondition
evidence，否则当前 Reporter 仍会保守输出 `uncertain`。

P0 实现必须二选一：

1. 把 verified `ExecutionEvidence` 转成 `confirmed_plan_context.postconditions`。
2. 或扩展 `TaskResultReporter._check_postconditions()`，让它读取
   `execution_payload` / `confirmed_plan_context` 中的 structured postcondition evidence。

P0 `verified` 条件：

```text
replay_summary.replay_status in ("succeeded", "observed")
replay_summary.drift_status == "none"
replay_summary.error is empty
execution_evidence 中存在：
  kind = "dom_text_present"
  status = "verified"
  target = slot_overrides.record_name
```

不满足这些条件时，Reporter 不得输出 `verified`。例如 replay succeeded 但缺少
postcondition evidence，必须继续输出 `uncertain` 或 `needs_review`。

### 13.5 回复示例

`verified`：

```text
执行完成。我在列表中看到了“测试项目B”，所以可以确认新增项目成功。
```

`uncertain`：

```text
操作已经执行，但我还没有拿到足够页面证据确认结果。建议你查看列表是否出现了“测试项目B”。
```

`needs_review`：

```text
操作执行后，我没有在列表中确认看到“测试项目B”。可能页面更新较慢，也可能操作没有成功。你可以让我重试，或者重新学习这个操作。
```

`blocked`：

```text
我找到了已学习路径，但当前页面和学习时的页面不匹配，所以没有继续执行。请确认是否打开了正确的页面。
```

`failed`：

```text
执行过程中遇到问题，这次没有完成新增项目。你可以让我重新执行，或者重新学习这个操作。
```

## 14. TaskPathPlanner 定位

### 14.1 当前定位

```text
TaskPathPlanner 已实现，是 L3 deterministic service。
它不进入包 1 的 P0 happy path。
```

### 14.2 不要这样接

```text
每次 execute_operation
  -> 必须经过 TaskPathPlanner
  -> 再执行 replay
```

这样会把单路径 happy path 复杂化。

### 14.3 应该这样接

| 场景 | 是否使用 TaskPathPlanner |
|---|---:|
| 只有一个 learned action 且目标明确 | 否，直接 replay |
| 多个 learned actions 可能匹配 | 是 |
| 用户目标模糊 | 是 |
| planning preview API path | 是 |
| 复杂组合任务 | 是 |
| 包 1 `/records` 新增 happy path | 否 |

## 15. `pending_choice` 目标设计

### 15.1 当前状态

`pending_choice` 是新增能力，不是当前已实现状态。它不进入包 1。

### 15.2 触发条件

| 条件 | 示例 |
|---|---|
| 多个 learned actions 同时匹配 | “帮我处理一下这个页面” |
| 用户只给 URL | `http://localhost:<fixture-site-port>/records` |
| 低置信 intent | “搞一下” |
| 用户目标冲突 | “学习一下然后删掉” |
| 高风险操作 | 删除、提交、状态修改 |
| Planner 返回多个候选 | 多路径可达 |

### 15.3 Contract

```ts
type PendingChoice = {
  type: "pending_choice";
  choiceGroupId: string;
  question: string;
  choices: Array<{
    choiceId: string;
    label: string;
    description?: string;
    intent:
      | "execute_operation"
      | "learn_operation"
      | "understand_page"
      | "cancel"
      | "other";
  }>;
  privateChoiceMapRef: string;
  turnsRemaining: number;
  createdAt: string;
};
```

### 15.4 核心安全规则

```text
用户和 LLM 可见层只暴露 choice_id。
真实 learned_path_id 只在 Orchestrator 内部解析。
Router 不得输出 learned_path_id。
```

## 16. `active_task` / RuntimeLedger 目标设计

### 16.1 当前状态

`active_task` / 完整 RuntimeLedger 是新增能力。当前主要已有：

```text
pending_intake
pending_target
last_no_path_reason
learned_actions
chat_headless / browser visibility
```

包 1 不大重构 ledger。

### 16.2 最小 contract

```ts
type ActiveTask = {
  task_id: string;
  kind:
    | "learn_operation"
    | "execute_operation"
    | "understand_page"
    | "clarify";
  target_url?: string;
  goal?: string;
  owner:
    | "runtime"
    | "learning_agent"
    | "web_operation_agent"
    | "page_understanding";
  status:
    | "collecting_requirements"
    | "waiting_for_user_input"
    | "learning"
    | "executing"
    | "reporting"
    | "completed"
    | "failed";
  created_at: string;
  updated_at: string;
};
```

### 16.3 状态标记规则

| 表述 | 状态 |
|---|---|
| 有 `pending_intake` 时继续补字段 | 当前已有 |
| 有 `pending_target` 时继续目标追问 | 当前已有 |
| 有 `pending_choice` 时用户选 A | 目标行为，包 2 新增 |
| 有 `active_task` 时继续 active task | 目标行为，包 2/3 新增 |
| TaskPathPlanner 多候选规划 | service 已有，chat 接入是包 4 |

## 17. 场景流转表

### 17.1 基础对话

| 场景 | 用户输入 | Entry Gate | Intake | Router | Runtime 裁决 | 状态写入 | 回复 |
|---|---|---|---|---|---|---|---|
| 问候 | “你好” | 不进 heavy runtime | 无 | 无 | 直接回复 | 普通消息 | 说明可以学习 / 执行网页操作 |
| 能力询问 | “你能做什么？” | 不进 heavy runtime | 无 | 无 | 直接回复 | 普通消息 | 说明支持学习网页操作、执行已学操作 |
| 非网页任务 | “帮我写文案” | unsupported / no-path | 无 | 无 | 引导回网页操作 | `CHAT_NO_PATH` 可选 | 说明当前主要处理网页操作 |
| 模糊输入 | “搞一下” | 进入 runtime | low confidence | ask | 追问 | no-path reason | 询问要学习还是执行什么 |

### 17.2 URL / 页面理解

| 场景 | 用户输入 | Intake | Router | Runtime 裁决 | Skill / Worker | 状态写入 | 回复 |
|---|---|---|---|---|---|---|---|
| 只发 URL | `/records` URL | target 有，goal 缺 | ask_user | 保存 `pending_target` | `ask_user_for_missing_info` | `pending_target` | “我已记住页面地址，你想学习或执行哪个操作？” |
| 要求看页面 | “看看这个页面能做什么” | inspect / understand | inspect / understand | 调页面理解 | `inspect_target_page` -> `understand_page` | page context trace | 页面摘要 + 追问目标 |
| 页面不可访问 | URL 无法打开 | inspect | inspect | 阻断 | inspect failed | no-path reason | 说明无法检查页面 |
| URL 中途变化 | pending A，用户给 B | provide new target | ask | 清旧 pending 或重建 | 无 | new pending | 要求重新确认目标 |

### 17.3 P0 学习新增项目 A

用户：

```text
学习新增项目，名称叫测试项目A
```

| 步骤 | 组件 | 行为 |
|---:|---|---|
| 1 | Entry Gate | 进入 heavy runtime |
| 2 | Intake Agent | 识别 `learn_operation` |
| 3 | Runtime | 提取 `record_name=测试项目A` |
| 4 | Runtime | 生成 `fill_values.record_name=测试项目A` |
| 5 | Context Collector | 收集 target、pending、learned actions |
| 6 | Router | 推荐 Learning Agent / `start_learning` |
| 7 | Runtime Adjudicator | 校验信息完整 |
| 8 | Learning Agent Boundary | 组织 learning request |
| 9 | `start_learning` | 学习页面操作，生成 LearnedPath |
| 10 | LearnedPath Parameterizer | 给匹配的 fill action 写 `value_slot=record_name` |
| 11 | Runtime | 更新 learned_actions |
| 12 | Response | 回复学习完成，说明项目名称可替换 |

成功回复：

```text
学习完成。我已经学会了“新增项目”这个操作，并且识别到项目名称是可替换参数。之后你可以说“帮我新增项目，名称叫 xxx”。
```

参数绑定失败回复：

```text
学习完成了一部分，但我没有可靠识别出“项目名称”对应的输入动作。为了避免之后重复填入固定值，建议你重新学习一次新增项目操作。
```

### 17.4 P0 执行新增项目 B

用户：

```text
帮我新增项目，名称叫测试项目B
```

| 步骤 | 组件 | 行为 |
|---:|---|---|
| 1 | Entry Gate | 进入 heavy runtime |
| 2 | Intake Agent | 识别 `execute_operation` |
| 3 | Runtime | 提取 `record_name=测试项目B` |
| 4 | Context Collector | 找到唯一匹配的“新增项目” learned action |
| 5 | Runtime Adjudicator | 检查 LearnedPath 有 `value_slot=record_name` |
| 6 | Runtime | 构造 `slot_overrides.record_name=测试项目B` |
| 7 | Runtime | 构造 `evidence_targets.dom_text_present=测试项目B`，并限定 `selector=[data-testid='record-list']` |
| 8 | Web Operation Agent Boundary | 组织 replay request |
| 9 | run_replay | 对 fill action 应用 slot override |
| 10 | run_replay | 实际填入 `测试项目B` |
| 11 | Evidence Capture | runtime stop 前采集 DOM evidence |
| 12 | Reporter Adapter | replay result + evidence -> reporter input |
| 13 | TaskResultReporter | 输出 outcome |
| 14 | Response | 返回保守结果 |

成功回复：

```text
执行完成。我在列表中看到了“测试项目B”，所以可以确认新增项目成功。
```

### 17.5 执行但未学习

用户：

```text
帮我新增项目，名称叫测试项目C
```

但没有 learned action。

| 步骤 | 组件 | 行为 |
|---:|---|---|
| 1 | Intake | 识别 `execute_operation` |
| 2 | Context Collector | learned_actions 为空 |
| 3 | Runtime Adjudicator | 阻断直接 replay |
| 4 | Runtime | 写 `last_no_path_reason` |
| 5 | Response | 提示先学习 |

回复：

```text
我还没学过“新增项目”这个操作。你可以先说“学习新增项目，名称叫测试项目A”，我学会后就可以帮你执行。
```

### 17.6 执行但 path 不支持参数化

用户：

```text
帮我新增项目，名称叫测试项目B
```

有 learned path，但没有 `value_slot=record_name`。

| 步骤 | 组件 | 行为 |
|---:|---|---|
| 1 | Runtime | 找到 learned path |
| 2 | Runtime | 检查发现无 `value_slot=record_name` |
| 3 | Runtime | 阻断 replay |
| 4 | Response | 要求重新学习 |

回复：

```text
我找到了已学习的“新增项目”路径，但它还不是可参数化路径，不能安全地把项目名替换成“测试项目B”。请重新学习一次新增项目操作。
```

### 17.7 多候选，目标行为

这是包 2 / 包 4，不是 P0。

已有：

```text
新增项目
搜索项目
删除项目
```

用户：

```text
帮我处理一下这个页面
```

| 步骤 | 组件 | 行为 |
|---:|---|---|
| 1 | Intake | 目标模糊 |
| 2 | Context Collector | 多个 learned actions |
| 3 | TaskPathPlanner | 返回多个候选 |
| 4 | Runtime | 写 `pending_choice` |
| 5 | Response | 给 A/B/C |

回复：

```text
你想让我做哪个操作？

A. 新增项目
B. 搜索项目
C. 删除项目
D. 学习一个新操作
```

### 17.8 用户取消，目标行为

| 场景 | 输入 | 当前 / 目标 | 行为 |
|---|---|---|---|
| 取消 pending | “算了” | 当前应已有部分 command 清理 | 清 `pending_intake`、`pending_target` |
| 取消 choice | “算了” | 包 2 新增 | 清 `pending_choice` |
| 取消 active task | “算了” | 包 2/3 新增 | 停止或标记 active task cancelled |
| 取消后回复 | “算了” | 目标 | “已取消当前任务。” |

## 18. P0 验收标准

### 18.1 `/records` 页面验收

| 编号 | 测试 | 期望 |
|---|---|---|
| IT-1 | 打开 `/records` | 页面可访问 |
| IT-2 | 输入项目名 | 可输入 |
| IT-3 | 点击新增 | 列表出现新项目 |
| IT-4 | 操作状态 | 显示新增成功或等价状态 |
| IT-5 | `data-testid` | Playwright / Agent 可稳定定位 |

### 18.2 学习参数化验收

| 编号 | 测试 | 期望 |
|---|---|---|
| LP-1 | 用户说“学习新增项目，名称叫测试项目A” | Intake 识别 `learn_operation` |
| LP-2 | Runtime fill values | 有 `record_name=测试项目A` |
| LP-3 | `start_learning` | 成功生成 LearnedPath |
| LP-4 | LearnedPath actions | 至少一个 fill action 有 `value=测试项目A` |
| LP-5 | 参数绑定 | 该 fill action 有 `value_slot=record_name` |
| LP-6 | 学习回复 | 说明项目名称是可替换参数 |
| LP-7 | 绑定失败 | 不允许标成完整可参数化路径 |

### 18.3 执行参数替换验收

| 编号 | 测试 | 期望 |
|---|---|---|
| EX-1 | 用户说“帮我新增项目，名称叫测试项目B” | Intake 识别 `execute_operation` |
| EX-2 | Runtime slot | 有 `record_name=测试项目B` |
| EX-3 | ReplayRequest | 有 `slot_overrides.record_name=测试项目B` |
| EX-4 | Replay 执行 | fill action 实际使用 B，不是 A；step log / debug trace 可证明 effective value |
| EX-5 | 页面结果 | 列表出现 `测试项目B` |
| EX-6 | 反向保护 | 不新增录制值 `测试项目A` |
| EX-7 | 无参数绑定 | Runtime 阻断，不执行固定值 replay |

### 18.4 Evidence 验收

| 编号 | 测试 | 期望 |
|---|---|---|
| EV-1 | replay 完成后 | runtime stop 前采集 evidence |
| EV-2 | 目标文本存在 | 优先在 `[data-testid='record-list']` 内查找，命中后 `ExecutionEvidence.status=verified` |
| EV-3 | 目标文本不存在 | `status=missing` 或 `unknown` |
| EV-4 | 无法检查 DOM | `kind=unknown` |
| EV-5 | Reporter 输入 | 包含 replay status + execution evidence |

### 18.5 Reporter 验收

| 编号 | 场景 | 期望 outcome |
|---|---|---|
| RP-1 | replay succeeded + evidence verified | `verified` |
| RP-2 | replay succeeded + no evidence | `uncertain` |
| RP-3 | replay failed | `failed` |
| RP-4 | page drift / unsupported | `blocked` 或 `needs_review` |
| RP-5 | evidence missing target | `needs_review` |

### 18.6 保守性验收

| 编号 | 场景 | 期望 |
|---|---|---|
| S-1 | 无 learned action | 不执行，提示先学习 |
| S-2 | path 无 `value_slot=record_name` | 不执行，提示重新学习参数化路径 |
| S-3 | replay 成功但 evidence 缺失 | 不说成功 |
| S-4 | Router 输出执行细节 | schema / runtime reject |
| S-5 | Router 推荐 `learn_then_execute` | runtime 保守阻断 |
| S-6 | 敏感字段进入 trace | 禁止 |

## 19. 后续包验收标准

### 19.1 包 2：pending_choice / ledger

| 编号 | 测试 | 期望 |
|---|---|---|
| PC-1 | 多候选 learned actions | 生成 `pending_choice` |
| PC-2 | 用户输入 `A` | 代码命中 choice |
| PC-3 | choice 可见 payload | 只有 `choice_id`，无 `learned_path_id` |
| PC-4 | choice 过期 | 自动清理 |
| PC-5 | 用户说“算了” | 清 pending |
| AT-1 | 学习 / 执行开始 | 写最小 `active_task` |
| AT-2 | 任务完成 | 标记 completed |
| AT-3 | 任务失败 | 标记 failed |

### 19.2 包 3：基础失败恢复

| 编号 | 场景 | 期望 |
|---|---|---|
| FR-1 | replay 找不到元素 | 报告失败，建议重新学习 |
| FR-2 | URL 不匹配 | 阻断并要求确认 |
| FR-3 | evidence 不足 | `needs_review` / `uncertain` |
| FR-4 | 用户选择重试 | 重新 replay |
| FR-5 | 用户选择重新学习 | 进入学习分支 |
| FR-6 | 用户选择取消 | 清状态 |

### 19.3 包 4：TaskPathPlanner chat 接入

| 编号 | 场景 | 期望 |
|---|---|---|
| TP-1 | 多个 learned actions | Planner 给候选 |
| TP-2 | 用户目标模糊 | 进入 pending_choice |
| TP-3 | 用户选择 choice | Runtime 内部解析真实 path |
| TP-4 | LLM 可见内容 | 不含 `learned_path_id` |
| TP-5 | 单路径明确目标 | 不走 Planner，直接 replay |

## 20. Codex 施工规则

```text
1. 目标是做出真实可工作的 WebAgentFlow，不是机械遵守旧 M11 切分。
2. 必要缺口可以提前加入，但必须拆成可验收施工包。
3. 第一施工包只做：
   新增 /records
   -> record_name slot extraction
   -> 学习新增项目 A
   -> LearnedPath action value_slot 参数绑定
   -> 执行新增项目 B
   -> replay slot_overrides 替换 A 为 B
   -> replay 结束前采集 ExecutionEvidence
   -> TaskResultReporter 保守回复。
4. /records 是新增到 apps/fixture-site 的测试页，当前不是已有路由。
5. _fill_values_from_intake 必须支持 record_name。
6. 学习阶段必须把 record_name 学习值绑定到对应 fill action。
7. ReplayRequest 必须新增 slot_overrides，至少支持 record_name。
8. ReplayAction 必须新增 value_slot 或等价参数绑定字段。
9. _build_replay_actions 必须读取 value_slot。
10. run_replay 必须接受 slot_overrides，并在执行 fill action 前应用 override。
11. 如果用户提供 record_name 但 LearnedPath 没有 record_name 参数绑定，Runtime 必须阻断，不能用固定录制值执行。
12. ExecutionEvidence 是新增 / 扩展 contract，不要假设当前 TaskResultReporter 已经直接消费该结构。
13. Internal Runtime Adapters 不是 Application Skills，不得出现在 Router skill menu，也不得由 LLM agents 直接请求。
14. Evidence 必须在 Playwright runtime.stop() 前采集。
15. P0 evidence 至少支持 dom_text_present 和 unknown；dom_text_present 优先限定在 [data-testid='record-list']。
16. P0 测试 record_name 必须唯一，例如 测试项目B-${timestamp}。
17. TaskResultReporter 原生 outcome 使用 verified / failed / uncertain / needs_review / blocked。
18. Reporter Adapter 必须让 TaskResultReporter._check_postconditions() 读到 structured postcondition evidence，否则 verified path 不算打通。
19. 如果 UI 需要 success / partial_success，只能做 wrapper mapping，不要改写 reporter 原生语义。
20. TaskPathPlanner 已实现，但不进入 P0 单路径 happy path。
21. TaskPathPlanner 只用于多候选 / planning preview / 复杂目标。
22. pending_choice 是新增能力，放到第二施工包。
23. pending_choice 可见层只暴露 choice_id，不暴露 learned_path_id。
24. active_task / RuntimeLedger 是新增最小 contract，放到第二或第三施工包，不在第一包大重构。
25. learn_then_execute 当前继续保守阻断，除非新增显式用户确认链路。
26. Router 只能建议，不能输出 selector、playwright、browser_action、learned_path_id 或直接调用 skill。
27. 所有 skill 调用必须经过 code-owned Runtime / Orchestrator。
28. Learning Agent 只能组织 start_learning 请求，不能直接调用 Web Operation Agent。
29. Web Operation Agent 只能在 matched learned action 存在时组织 start_replay。
30. Page Understanding Service 只负责 inspect / understand，不拥有 start_learning。
31. ask_user_for_missing_info 必须写 pending，不允许只回复一句话就丢上下文。
32. 敏感字段不得进入 agent trace、router trace、progress event。
33. P0 验收必须证明 replay 实际填入的是“测试项目B”，不是学习时录制的“测试项目A”；step log / debug trace 必须能证明 effective value。
34. <fixture-port> 只是示例端口，contract 使用 runtime target URL，不硬编码本地端口。
35. 执行结果必须基于 evidence 保守报告。
36. 文档状态要同步本地代码状态，避免 roadmap 与代码漂移。
```

## 21. 推荐执行顺序

### 21.1 第一轮：文档同步包

```text
同步 docs / roadmap / M11 plan
标清当前 conversation runtime pieces 已存在
标清 /records 是新增页面
标清 TaskPathPlanner / TaskResultReporter 已实现
标清 TaskPathPlanner 不进 P0
标清 TaskResultReporter 需要 ExecutionEvidence adapter
标清 pending_choice / active_task 是新增能力
```

### 21.2 第二轮：`/records` 参数化闭环包

```text
新增 /records
实现新增项目 UI
实现 record_name slot extraction
扩展 _fill_values_from_intake
学习新增项目 A
写 LearnedPath
给 fill action 绑定 value_slot=record_name
执行新增项目 B
ReplayRequest.slot_overrides
ReplayAction.value_slot
run_replay 应用 slot override
runtime stop 前采集 DOM evidence
Reporter adapter
TaskResultReporter 保守回复
```

### 21.3 第三轮：`pending_choice` / ledger 包

```text
pending_choice
choice_id 私有映射
最小 active_task
pending 清理 / 过期
cancel 统一处理
```

### 21.4 第四轮：基础恢复包

```text
执行失败报告
URL 不匹配阻断
元素找不到 -> 重新学习建议
A. 重试 B. 重新学习 C. 取消
```

### 21.5 第五轮：TaskPathPlanner chat 接入包

```text
多 learned actions
目标模糊
planning preview / confirmed execution
choice mode
```

## 22. 最终 P0 闭环定义

```text
用户：学习新增项目，名称叫测试项目A

系统：
1. 提取 record_name = 测试项目A
2. 学习新增项目操作
3. LearnedPath 记录 fill value = 测试项目A
4. Runtime 给该 fill action 加 value_slot = record_name
5. 回复：已学会新增项目，项目名称可替换


用户：帮我新增项目，名称叫测试项目B

系统：
1. 提取 record_name = 测试项目B
2. 找到“新增项目”的 LearnedPath
3. 检查 LearnedPath 支持 value_slot = record_name
4. 构造 slot_overrides.record_name = 测试项目B
5. replay 时把 fill action value 替换为测试项目B
6. 执行新增
7. runtime 关闭前检查 DOM 是否出现测试项目B
8. Reporter 输出 verified
9. 回复：执行完成，页面上已出现测试项目B
```

## 23. 收口判断

这版文档的关键不是继续扩大 Agent 图，而是先把第一条 working runtime 闭环钉牢：

```text
学会一个操作
按用户新输入参数执行这个操作
看到页面结果
保守报告证据
```

只有这条跑通，后续 `pending_choice`、`active_task`、Failure Recovery、
TaskPathPlanner 接入才有真实地基。
