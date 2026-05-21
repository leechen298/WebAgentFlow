# 11.3.5 · Customer-Facing Agent Router & Skill Runtime

状态：planning_refined（working runtime v6 施工稿已落库，后续执行包尚未展开）
里程碑：M11
类型：code

## 迭代定位

M11.3.4 已把 `wagent chat` 从纯规则入口推进到 Conversation Intake Agent：
LLM / fallback 可以把用户语言转成结构化 intent、target、action、slots 和
missing fields，代码继续负责 schema 校验、scope、执行策略、response provenance
和脱敏 LLM trace。

人工 smoke 暴露出下一层产品问题：系统虽然调用了 Intake Agent，但仍像规则机器人。
用户只输入 URL 时，系统会把它当作执行请求；用户下一句说“学习”时，系统又不能把它
和上一轮 URL 连起来。根因不是一个正则 bug，而是面客 Agent 路由和应用能力边界没有
产品化设计清楚：

```text
用户表达目标
-> 系统应收集上下文和页面线索
-> Router 判断下一步交给哪个工作 Agent / skill
-> Orchestrator 做代码侧裁决
-> Skill Runtime 执行应用能力
-> Result Reporter 统一回复用户
```

本轮把 11.3.5 从“聊天上下文恢复”升级为 **Customer-Facing Agent Router &
Skill Runtime / 面客 Agent 路由与应用技能运行时**。

## 核心原则

```text
Customer-Facing Agent Router != Conversation Orchestrator.
Router 只建议下一步交给谁。
Orchestrator 判断这个建议能不能执行。
Skill Runtime 才执行应用能力。
```

LLM 不直接控制浏览器。LLM 负责理解、路由建议和页面语义判断；代码负责状态、
scope、MVP 边界、授权、事件和真正调用能力；Learning / Replay / Runtime services
负责真实浏览器工作。

## 为什么需要本轮

当前系统已经具备不少底层能力：

- HTML -> Full AST：`apps/api/app/services/html_ast_parser.py`
- Full AST -> Simplified AST：`apps/api/app/services/ast_simplifier.py`
- live page analysis：`apps/api/app/services/learning/page_analyzer.py`
- form label extraction：`apps/api/app/services/analysis/form_label_extractor.py`
- rule-based action planning：`apps/api/app/services/learning/action_planner.py`
- shared action execution：`apps/api/app/services/execution/action_executor.py`
- Playwright runtime：`apps/api/app/services/execution/execution_runtime.py`
- product-level learning：`apps/api/app/services/learning/learning_run_service.py`
- LearnedPath data model：`apps/api/app/models/learned_path.py`
- LearnedPath persistence / retrieval：`apps/api/app/repos/learned_paths_repo.py`
- replay / observation evidence：`apps/api/app/services/learning/learned_path_replay.py`
- wait / observation signals：`apps/api/app/services/learning/wait_for_change.py`、
  `apps/api/app/services/learning/replay_observation.py`
- Result Reporter inputs：`replay_observation.py` 产生的 observation evidence 可用于
  用户可见结果反馈，不只是 replay 内部证据。
- task planning domain schemas：`apps/api/app/schemas/task_planning.py`
- response provenance / LLM trace：`apps/api/app/services/conversation/provenance.py`

这些基础设施已经接近“让 Agent 看懂页面、查自己会不会、决定下一步”的骨架。
11.3.5 的目标不是重造浏览器执行层，而是把这些能力整理成面客路由层可以使用的
Application Skill Registry，并把工作 Agent 的职责边界写清楚。

## 本轮目标

- 定义 Customer-Facing Agent Router，和 Conversation Orchestrator 分开。
- 定义 Application Skill Registry / Skill Registry：应用能力菜单，不是 Agent 列表。
- 定义 Learning Agent、Web Operation Agent、Page Understanding Agent 在 11.3.5
  MVP 中的职责。
- 把 HTML AST、Simplified AST、PageAnalysis、operation path / LearnedPath 证据纳入
  Page Understanding / routing context。
- 定义 Router -> Orchestrator -> Worker Agent -> Skill Runtime 的受控执行链。
- 定义 target resolution、MVP 高影响动作边界、thinking policy、progress / loading 和 history
  trace 规则。
- 收口裸 URL、短句“学习”、no-path 学习引导这些小白用户体验问题，但不把本轮
  降格为单个 bugfix。

## 明确不做

- 不做 active browser tab 读取。M11.3.5 MVP 仍以用户聊天输入、pending state 和
  current-session learned actions 为目标来源。
- 不让 Router 直接调用 skill。
- 不让任何 LLM 输出 selector、Playwright step、browser action list 或 learned_path_id
  作为执行授权。
- 不实现正式 Risk Policy、consent gate 或权限系统；明显高影响 / 不可逆动作不进入
  本轮自动 learn_then_execute。
- 不实现完整 M12 recovery / retry / abort。
- 不实现复杂多页面 workflow。
- 不做真实业务系统适配。
- 不重新引入已移除的旧用户操作录制 / Chrome extension 栈。

## Working Runtime 后续拆包

11.3.5 是 `wagent chat` 面客 Agent 路由与应用技能运行时的父包。当前后续工作不另起
11.4，也不只挂在 11.3 总纲里；统一按 11.3.5.x 拆成可验收、可回滚的小包。

完整施工稿见：

- [`working-runtime-construction.md`](./working-runtime-construction.md)
- [`working-runtime-iteration-plan.md`](./working-runtime-iteration-plan.md)

注意：

- 11.3.5.2 目录已经存在，继续作为 Chat Task State Reducer、learning preconditions、
  working runtime 总设计和测试入口的锚点，暂不为了改名而迁移目录。
- `product-test-site /items`、参数化 replay、ExecutionEvidence、Reporter 接入、
  `pending_choice`、`active_task`、基础恢复和 TaskPathPlanner chat 接入不得塞进一个
  大迭代。
- 第一条 P0 闭环必须证明“学习新增项目 A -> 执行新增项目 B”真的填入 B，而不是复用
  学习时录制的固定值 A。
- `TaskPathPlanner` 和 `TaskResultReporter` 已有 deterministic service 实现，但不代表
  它们应该进入所有 `wagent chat` 分支。单路径 happy path 先直接 replay；多候选 /
  planning path 再接 TaskPathPlanner。
- `ExecutionEvidence` 是新增 / 扩展 contract。现有 Reporter 需要 adapter 才能消费
  replay result + 页面证据。
- “学习新增 A -> 执行新增 B”依赖参数化学习 / replay slot override；不能只靠固定
  LearnedPath action value 重放。

| Package | 目标 | 先做 |
|---|---|---|
| 11.3.5.2 | 文档同步 + working runtime 总设计 + task state reducer / learning preconditions | 是 |
| [11.3.5.3](../11.3.5.3-product-test-site-items-fixture/) | `apps/product-test-site` 新增 `/items` 列表测试页 | 是 |
| [11.3.5.4](../11.3.5.4-parameterized-learning-replay-slots/) | `item_name` slot + `value_slot` / `slot_overrides` 参数化 learning / replay | draft_docs |
| 11.3.5.5 | ExecutionEvidence + TaskResultReporter adapter，runtime stop 前采集 DOM evidence | 是 |
| 11.3.5.6 | `wagent chat` `/items` 学习 / 执行闭环测试方案与结果记录 | 是 |
| 11.3.5.7 | `pending_choice` + 最小 `active_task` ledger | 后续 |
| 11.3.5.8 | 基础失败恢复 | 后续 |
| 11.3.5.9 | TaskPathPlanner 多候选 chat 接入 | 后续 |

## 文档

- `working-runtime-construction.md`
- `working-runtime-iteration-plan.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`
