# 实施计划

> 本文件是 M11.0 总纲。具体实现拆分见 `../m11-plan.md`，不要一次性实现
> 本文件全部内容。

## 触及的文件 / 模块

> 本文是规划文档。以下是 planned modules，不表示这些文件或目录当前已经存在。

- `apps/cli/` —— planned runtime conversation CLI 入口；必须区别于当前
  `wagent verify`。
- `apps/api/app/services/conversation/` —— planned session / message /
  orchestrator service area。
- `apps/api/app/schemas/conversation.py` —— planned request / response /
  event schemas。
- `apps/api/app/routers/conversation.py` —— planned runtime conversation
  endpoint。
- `apps/api/app/models/conversation_session.py` 或 JSON / event store ——
  planned session persistence；是否落库待实现时确认。
- `apps/api/app/services/learning/learned_path_replay.py` —— existing M10
  replay capability；M11.0 只规划如何被 orchestrator 显式调用，不改
  replay contract。
- `docs/testing/features/conversation.md` —— future conversation testing
  domain matrix；本轮只规划，不创建。
- `apps/e2e/tests/conversation/` —— future E2E location；本轮不实现。

## Runtime surfaces 区分

1. 当前 `wagent verify` / `verify-scenario`
   - development verification skill backend。
   - 用于 auditable scenario checks。
   - 不是 runtime conversation surface。

2. M11.0 runtime conversation CLI
   - 用户和 WebAgentFlow 对话的最小入口。
   - 管理 session、message、status、pause、abort、takeover、replay smoke
     hook。
   - 当前规划对象。

3. M16 external CLI / Skill / Tool
   - 稳定对外接口。
   - 给 external scheduler / scripting / integration 使用。
   - 不属于 M11.0。

## 推荐状态模型

M11.0 planned session states：

- `idle`
- `task_intake`
- `awaiting_confirmation`
- `replay_requested`
- `replay_running`
- `paused`
- `abort_requested`
- `takeover_requested`
- `completed`
- `failed`

这些状态是 M11.0 的 orchestrator 骨架。Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H） 相关状态
可以预留边界，但不实现具体 Agent 逻辑。L3 per-step browser control 不允许
进入状态机。Replay states 只允许显式 path replay，不做 path selection。

## 推荐命令 / 消息

CLI-first 初版可支持：

- `/status`
- `/cancel`
- `/pause`
- `/resume`
- `/abort`
- `/takeover`
- `/replay <learned_path_id> <url>`
- free-form task text

`/replay` 是 M11.0 最小可执行桥：只调用已完成的 M10 replay API / service。
`/replay` 需要显式 `learned_path_id + url`，不做 path selection。

Free-form task text 在 M11.0 只记录为 task input，不进入 Task Path Planner / 任务路径规划器（legacy: Agent D） planning。
自然语言 task-to-path 是 M11.1，不在 M11.0。

## 最小数据结构规划

```text
ConversationSession
- id
- status
- current_mode
- created_at
- updated_at
- metadata

ConversationMessage
- id
- session_id
- role: user | system | agent | engine
- content
- created_at
- metadata

ConversationEvent
- id
- session_id
- type
- payload
- created_at
```

是否落库待实现时确认。第一版可以先用 DB，也可以先用 JSON / event log。
实现时需要权衡：

- DB：便于 history、audit、API 查询和后续 E2E；成本是 migration 和模型设计。
- JSON / event log：便于快速验证 CLI loop；成本是查询、并发和恢复能力较弱。

不加入路线图外的归属、范围或身份管理字段。

## Orchestrator 边界

Conversation Orchestrator / Dispatcher 的输入：

- user message
- slash command
- engine event
- replay result
- abort / pause / resume signal

输出：

- next state
- user-facing response
- optional engine command
- audit event

禁止：

- 不能直接让 LLM 决定下一步浏览器 click / fill。
- 不能调用 autonomous run 重新学习。
- 不能把 M10 replay result 包装成 `pass_gate` 或 Supervisor verdict。

## 步骤

1. 定义 conversation shell contract
   - 明确 CLI 输入 / 输出边界。
   - 明确 session 创建、消息追加、状态查询和关闭语义。
   - 明确当前 `verify-scenario` CLI 不进入 runtime conversation flow。

2. 定义 session state 和 message / event schema
   - 固定状态枚举。
   - 固定 message role 和 event type 的最小集合。
   - 记录哪些字段是 M11.0 必需，哪些是 M11.1+ placeholder。

3. 设计 CLI command parser
   - 支持 `/status`、`/pause`、`/resume`、`/abort`、`/takeover`、
     `/cancel`、`/replay <learned_path_id> <url>`。
   - Free-form task text 只入 session，不触发 Task Path Planner / 任务路径规划器（legacy: Agent D）。

4. 设计 Orchestrator / Dispatcher service boundary
   - 输入 user message / slash command / engine event。
   - 输出 next state、user-facing response、optional engine command 和 audit
     event。
   - 代码侧执行 L3 不允许 LLM 逐步浏览器控制的不变量。

5. 设计 explicit replay hook
   - `/replay <learned_path_id> <url>` 显式调用 M10 replay 能力。
   - 不做 candidate selection。
   - 不修改 replay request / response contract。

6. 设计 API / CLI interaction flow
   - CLI 可以通过 planned conversation endpoint 创建 session、追加消息和读取
     status。
   - 如果先不落库，CLI 也必须输出可审计 transcript。
   - API 和 CLI 都必须从 WebAgentFlow 视角输出，不暴露内部 Agent 作为用户
     直接沟通对象。

7. 设计 testing strategy
   - 建立 conversation 测试域。
   - 覆盖 command parser、state transition、orchestrator dispatch、replay
     command dispatch。
   - 不依赖 LLM provider，不调用 autonomous run。

## Testing strategy

本节只规划，不实现。

- M11.0 后续应建立 `conversation` 测试域。
- 单元测试：command parser、state transition、orchestrator dispatch。
- API tests：session create、message append、status query、replay command
  dispatch。
- CLI tests：slash command parsing、session lifecycle。
- E2E：可以后续放 `apps/e2e/tests/conversation/`，但不是本轮文档创建任务。
- 不依赖 LLM provider。
- 不调用 autonomous run。

## 验证

因为本轮只写文档，验证包括：

- `git diff --check`
- 文档中没有出现 10.3 作为下一迭代。
- 文档中明确 M11.0 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
- 文档中明确 CLI runtime conversation、M16 external CLI、当前
  `verify-scenario` CLI 三者不同。
- 文档中明确不调用 autonomous run。
- 文档中明确不引入路线图外的产品外壳、身份管理、托管数据或外部通道规划。
