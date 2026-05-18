# 11.3.5 · Customer-Facing Agent Router & Skill Runtime

状态：proposed（docs generated, implementation not started）
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
- LearnedPath persistence / retrieval：`apps/api/app/repos/learned_paths_repo.py`
- replay / observation evidence：`apps/api/app/services/learning/learned_path_replay.py`
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

## 文档

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`
