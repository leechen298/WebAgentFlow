# 11.3.5.2 · Chat Task State Reducer & Learning Preconditions

状态：draft_requirements
里程碑：M11
类型：code
父迭代：11.3.5 · Customer-Facing Agent Router & Skill Runtime
前置相关：11.3.5.1 · Conversation Entry Gate & Chat Latency UX

## 一句话目标

把 `wagent chat` 从“每轮按单句意图直接 learn / execute”升级为“每轮根据当前输入和会话状态推导下一步”的任务状态推进入口；在学习前守住必要前置条件，并把学习失败转成用户能理解、能继续操作的反馈。

## 与 11.3.5.x Working Runtime 的关系

本目录继续作为 11.3.5.x working runtime 的当前规划锚点，不为了改名迁移目录。
它负责沉淀文档同步、任务状态推进、learning preconditions 和测试入口；后续实现拆成
独立小包推进：

完整 working runtime 施工稿放在父包：

- [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md)

| Package | 目标 |
|---|---|
| 11.3.5.3 | `apps/fixture-site` 新增 `/records` 列表测试页 |
| 11.3.5.4 | `record_name` slot + `value_slot` / `slot_overrides` 参数化 learning / replay |
| 11.3.5.5 | ExecutionEvidence + TaskResultReporter adapter，runtime stop 前采集 DOM evidence |
| 11.3.5.6 | `wagent chat` `/records` 学习 / 执行闭环测试方案与结果记录 |
| 11.3.5.7 | `pending_choice` + 最小 `active_task` ledger |
| [11.3.5.8](../11.3.5.8-basic-failure-recovery/) | 基础失败恢复 |
| 11.3.5.9 | TaskPathPlanner 多候选 chat 接入 |

第一条 P0 闭环是 `/records` 新增项目：学习新增项目、按新输入参数化执行新增项目、
采集页面证据，并由 TaskResultReporter 保守回复。该闭环必须证明 replay 实际填入
执行阶段用户提供的 `测试项目B`，不能复用学习阶段录制值 `测试项目A`。

## 背景问题

11.3.5.1 解决的是入口门禁和 CLI waiting 体验：哪些输入要进入网页任务 runtime，哪些输入快速友好回复。

人工试跑继续暴露出下一层问题：

- 明确网页任务进入 runtime 后，系统还没有稳定的任务状态推进。
- 用户只提供目标 URL 或只说“学习某个 URL”时，系统可能过早启动 learning。
- learning 启动后缺少操作目标或必要输入，最终返回内部错误，例如 `Learning run did not produce a LearnedPath`。
- 用户看不到“当前缺什么”“下一步该补什么”“是否可以继续学习或执行”。
- 浏览器已经打开时，CLI / response 仍可能只停留在粗粒度的“正在理解你的需求”，阶段反馈和真实动作不同步。

这个问题不应继续塞进 Entry Gate。Entry Gate 只负责“是否进入网页任务 runtime”。进入 runtime 后，必须由任务状态推进层决定下一步。

## 核心判断

`wagent chat` 应按 turn-based reducer 工作：

```text
当前用户输入
+ session metadata
+ active_task（canonical task state）
+ pending_target / pending_intake / last_no_path_reason（legacy compatibility input）
+ current-session learned actions
+ Entry Gate / Intake / Router result
+ 最近失败原因 / no-path reason
=> 下一步状态
=> 下一步用户反馈或 skill request
```

用户不会严格按系统流程输入。每一轮都应该重新根据状态判断：

- 是不是已经有目标页面？
- 是不是已经有操作目标？
- 是不是已有可复用 LearnedPath？
- 是不是缺必要输入？
- 是不是需要用户确认学习？
- 是不是可以开始 learning？
- learning 失败后是否还能继续补充信息？
- 是否应该清理当前 active task？

## 新增概念：active_task

建议在 session metadata 中增加 `active_task`，用于保存当前面客任务的可恢复状态。
11.3.5.2 实现后，`active_task` 是交互式网页任务的 canonical task state。
既有 `pending_target`、`pending_intake`、`last_no_path_reason` 只能作为兼容读取 /
迁移输入，不能再成为独立推进任务的第二套状态源。

示例结构：

```json
{
  "active_task": {
    "task_id": "<uuid-or-message-derived-id>",
    "target_url": "<target-url>",
    "site_origin": "<origin>",
    "target_source": "user_message_url",
    "goal": null,
    "canonical_goal": null,
    "slots": [],
    "stage": "target_collected",
    "proposed_next_action": "ask_operation_goal",
    "last_failure_reason": null,
    "created_from_message_id": "<message-id>",
    "updated_from_message_id": "<message-id>",
    "turns_remaining": 3
  }
}
```

原则：

- `active_task` 是代码侧状态，不是 LLM 记忆。
- LLM 可以帮助理解用户输入，但不能直接决定状态转移是否生效。
- Orchestrator / reducer 负责合并用户输入、校验 scope、更新 stage、调用 skill。
- `active_task` 只能记录 conversation / task state，不得写成 LearnedPath evidence。
- reducer 每轮输出后必须只写回一个 canonical `active_task`。如果实现阶段仍需要维护
  `pending_target` / `pending_intake` / `last_no_path_reason` 给旧代码读取，它们必须由
  `active_task` 派生或同步清理，不能反向覆盖 reducer 判断。
- 新 URL、显式取消、turns 用尽、学习成功、执行完成都必须定义清理 / 替换规则，避免
  旧 pending state 影响下一轮任务。

## 建议状态

第一版状态保持少而清晰：

| Stage | 含义 | 下一步 |
|---|---|---|
| `idle` | 没有活动任务 | 等待用户输入 |
| `target_collected` | 有目标 URL，但操作目标不明确 | 追问要学习或执行什么 |
| `goal_collected` | 有 URL 和操作目标 | 查找当前 session 是否已学过 |
| `need_required_inputs` | 已知目标和操作，但缺必要输入 | 追问用户补充输入 |
| `awaiting_learning_confirmation` | 当前 session 没有可用路径，需要用户确认是否学习 | 用户确认后进入 learning，取消则清理 |
| `learning` | 正在学习 | 记录 progress，等待 learning result |
| `learning_failed` | 学习失败但可继续 | 面客化说明原因，允许补充后重试 |
| `learned_ready` | 已学会，可执行 | 询问用户是否执行，或提示后续说法 |
| `awaiting_execution_confirmation` | 已学会，等待用户确认执行 | 用户确认后进入 executing，取消则清理 |
| `executing` | 正在执行已学路径 | 记录 progress，等待 replay result |
| `done` | 本轮任务完成 | 保留摘要或清理 active task |
| `blocked` | 当前不支持或信息不足无法继续 | 给出下一步建议 |

状态命名可以在技术设计阶段微调，但必须保留“每轮 reducer 推进”的语义。

状态推进原则：

- 任何确认类短句（例如“是”“可以”“学习”“执行”）只能作用于当前
  `active_task.stage` 明确等待确认的任务。
- 如果当前输入包含新的 URL、明确新的目标或明显改变任务，reducer 必须先判断是否替换
  当前 `active_task`，不能把确认绑定到旧任务。
- 如果没有 `active_task`，确认类短句不得触发 learning / replay；应追问用户提供页面和
  操作目标。
- 取消类输入在任何非 `idle` stage 都应清理 `active_task` 及其派生 pending state，并
  返回明确取消文案。

## 学习前置条件

`start_learning` 前必须满足：

1. `target_url` 明确。
2. `goal` / `canonical_goal` 明确，或 Page Understanding / 当前页面上下文能给出一个
   代码侧认可的 primary goal。
3. 必要输入齐全，或页面 / 操作被代码侧明确判定不需要输入。
4. 当前任务处于可学习 stage。
5. 不依赖 validation spec / assertions oracle 补输入。

如果缺任何一项，不得启动 learning，不得打开浏览器执行学习动作。

必要输入的第一版判定来源只能是：

- 用户消息 / pending intake 中已结构化提取的 slots。
- Page Understanding 输出的 `supported_goals[].required_slots[]`，但只能作为
  Orchestrator 追问和校验的输入，不能直接当作执行证据。
- 代码侧已知的低风险、无输入操作白名单；如果没有白名单，默认按“未知是否需要输入”处理。
- 用户在当前 `active_task` 上的明确补充或确认。

如果系统无法判断某个目标是否需要输入，默认进入 `need_required_inputs` 或
`target_collected` / `goal_collected` 后的追问，不得默认“无需输入”并启动 learning。
但对于 URL-only 输入，如果页面理解能识别主要操作，系统可以用该 primary goal 启动学习；
学习过程中发现缺用户信息时再进入可恢复追问。

应该进入追问，例如：

```text
我看到了这个页面地址。你想让我学习这个页面上的什么操作？请补充要学习的操作和需要填写的信息。
```

如果页面理解结果能提供候选目标，Orchestrator 可以用统一 WAgent 口径提出建议，但不能把页面理解结果写成事实证明。

## 已学路径查询与学习确认

当用户要求执行某个网页操作时，系统应先查询当前 session / target scope 下是否已有匹配 LearnedPath。

### 已学过

如果存在同 scope 的可用 LearnedPath：

- 可以按当前交互策略直接执行，或给出简短确认。
- 不得跨 target URL / site origin 误命中。

### 未学过

如果没有可用 LearnedPath：

- 不应直接返回冷冰冰的 no-path。
- 对 URL-only 或明确学习类输入，系统可以自动进入 learning，但必须先记录
  `active_task` 并输出用户可理解的学习阶段反馈。
- 对明确执行类输入，可以生成 `awaiting_learning_confirmation`，也可以按产品策略先学习；
  但不得直接 replay。
- 用户可通过确认类回复继续，例如“是”“可以”“学习”。
- 用户可通过取消类回复终止，例如“取消”“不用了”。
- 确认必须绑定当前 `active_task.task_id` / `target_url` / `canonical_goal`。如果用户在确认前
  提供了新 URL 或新目标，旧确认态必须失效，reducer 应先更新或替换 `active_task`。

建议用户反馈：

```text
我还没学过这个页面上的这个操作。要我现在学习吗？回复“是”开始学习，回复“取消”停止。
```

### 学习后是否自动执行

如果用户原始目标是执行，并且系统为了执行而学习：

- learning 成功后可以进入 `learned_ready`。
- 11.3.5.2 第一版采用保守策略：学习完成后进入 `awaiting_execution_confirmation`，
  明确询问用户是否执行。
- 用户确认执行后，reducer 才能进入 `executing` 并调用 replay。
- 第一版不做“学习成功后自动执行”。低影响 happy path 自动执行留给后续 risk /
  consent policy 更清楚以后再设计。

## 学习失败面客化

内部错误不能直接展示给用户。以下内部结果必须映射成用户可理解的反馈：

| Internal reason | User-facing direction |
|---|---|
| `missing_target_url` | 说明需要目标页面地址 |
| `missing_action_goal` | 说明需要知道要学习哪个操作 |
| `missing_required_inputs` | 说明需要补充必要输入 |
| `learning_run_no_learned_path` | 说明已尝试但没有学成可复用路径，并提示补充操作目标 / 输入 |
| `browser_error` | 说明浏览器或页面访问遇到问题，提示确认页面可访问 |
| `persistence_failed` | 说明保存学习结果失败，提示稍后重试 |

不得向普通用户展示：

```text
Learning run did not produce a LearnedPath.
```

这类内部错误只能进入 history / debug raw，并保持 redaction。

## Progress / 阶段反馈

11.3.5.1 的 CLI spinner 只能说明“请求仍在处理”。11.3.5.2 需要让后端阶段反馈更贴近真实动作。

本轮需要把 `wagent` 的一次消息结果重新定义为：

```text
用户输入
=> progress timeline（阶段性反馈，可实时显示，也可随结果回放）
=> final user_response（正式 WAgent 回复）
=> evidence references（events / metadata / learning / replay evidence）
```

也就是说，`wagent conversation send` 或后续测试入口不能只看最终 `user_response`。如果用户发
URL 后系统会打开页面学习，结果必须包含“正在查询已学记录 / 正在打开页面 / 正在理解页面 /
正在学习操作 / 需要用户协助 / 学习完成”等阶段性反馈。

参考 Codex CLI / Claude Code CLI 的原则不是复制视觉样式，而是采用同类 agentic CLI 沟通方式：

- 用户提交后立即看到系统在工作。
- 多阶段任务有可感知的进度，而不是一行“正在理解”后静默。
- 阶段状态和最终回复分离。
- 对复杂任务保留可回看的任务 / 事件 / evidence 轨迹。
- 中断或失败时说明当前卡在哪一步，以及用户能怎么继续。

建议事件：

- `task_state_transition`
- `learned_action_lookup_started`
- `learned_action_lookup_completed`
- `learning_precondition_blocked`
- `learning_confirmation_requested`
- `learning_started`
- `browser_opened`
- `learning_completed`
- `learning_failed`
- `execution_started`
- `execution_completed`

建议第一版 progress timeline 至少覆盖：

| Stage | User-facing progress | Trigger |
|---|---|---|
| `message_received` | `收到你的请求。` | CLI / API 收到用户消息 |
| `classifying_intent` | `正在判断这是不是网页任务。` | Entry Gate / Intake 开始 |
| `collecting_context` | `正在读取当前会话上下文。` | Context Collector 开始 |
| `lookup_learned_actions` | `正在查询是否已经学过这个页面。` | LearnedPath lookup 开始 |
| `opening_page` | `正在打开页面。` | 浏览器 / page context 开始 |
| `understanding_page` | `正在理解页面内容和可操作目标。` | Page Understanding 开始 |
| `learning_operation` | `正在学习这个页面的操作。` | Learning Service 开始 |
| `waiting_for_user_input` | `学习需要你补充必要信息。` | 发现账号 / 密码 / 验证码 / 用户判断缺失 |
| `learning_completed` | `学习完成，正在整理我学会了什么。` | LearnedPath 已生成 |
| `learning_failed_recoverable` | `这次还没学成，我正在整理需要你补充的信息。` | 未生成 LearnedPath 但可继续 |
| `executing_learned_path` | `正在执行已学操作。` | Replay 开始 |
| `final_response_ready` | `正在生成回复。` | Result Reporter 开始 |

如果暂时不做 streaming，dispatch response 至少应携带 `progress_timeline` 或等价 events
摘要，CLI 可以回放这些阶段；避免浏览器已打开但用户仍只看到“正在理解”。

最低可验收形态：

- dispatch response 必须包含非空 `user_response`，且 `user_response` 与 reducer 输出的
  next action 一致。
- dispatch result 或 history detail 必须能复原本轮 progress timeline。
- history detail 必须能看到 redacted `task_state_transition`、当前 / 下一 stage、blocked
  reason 或 learning failure raw reason。
- CLI 可以继续先打印最终 response，不要求本轮完成 streaming；但不得只停留在
  `正在理解你的需求` 这类与真实阶段不一致的文案。
- 内部 raw reason 可以进入 history / debug raw；普通用户回复必须使用面客化文案。

## 用户体验目标

### 输入普通问候

应快速回复并引导回 WebAgentFlow：

```text
你好，我可以帮你学习网页操作，也可以执行已经学会的操作。你可以发页面地址，或告诉我要做什么。
```

### 输入 URL + 执行目标

系统应进入网页任务 runtime，查找是否已学过。

如果未学过：

```text
我还没学过这个页面上的这个操作。要我现在学习吗？回复“是”开始学习，回复“取消”停止。
```

### 输入单独 URL

系统应先查询当前 session / target scope 下是否已有相关 LearnedPath / learned action。

如果已学过，应询问用户要执行、复习还是重新学习什么：

```text
我找到这个页面相关的已学操作。你想让我执行哪个操作，还是重新学习这个页面？
```

如果没学过，可以自动开始学习，并在学习完成后根据页面理解和操作记录报告学会了什么：

```text
我还没学过这个页面。我会先尝试学习它的主要操作。
```

如果学习中发现需要账号、密码、验证码或用户判断，应请求用户协助，而不是报告“无法学习”：

```text
我已经打开这个页面，但继续学习需要你提供账号和密码。你可以补充这些信息，或回复“取消”停止这次学习。
```

### 输入取消

清理当前 `active_task`：

```text
好的，已取消这次操作。
```

## 自动化评测规划

本轮先不直接编写 Python 测试文件。已新增
[`test-plan.md`](./test-plan.md) 作为本迭代测试入口；完整长期测试方案放在
[`docs/testing/features/wagent-chat-progress-evaluation.md`](../../../../testing/features/wagent-chat-progress-evaluation.md)。

评测重点：

- 从用户第一次调用 `wagent chat` 开始测。
- 同时覆盖已有会话上的 `wagent conversation send <session_id> --content <message>`。
- 第一批先做一轮对话、多条 case，不做长对话自动化。
- 单条消息评测先校验最终 `user_response`，再校验同一轮消息产生的过程日志 / events /
  metadata。
- 工作过程中的反馈通过结构化日志 / conversation events / progress timeline 最终校验，且必须
  能用 `session_id`、`message_id`、`event_id` 或 `run_id` 关联到本轮输入。
- `http://localhost:<fixture-port>/target-login` 这类 URL 输入需要先查询当前应用是否已有相关
  LearnedPath / learned action。
- 如果已有记录，应询问用户要执行、复习还是重新学习什么。
- 如果没有记录，可以自动开始学习，并在学习完成后根据网页理解和操作记录报告学会了什么。
- 如果学习需要账号、密码、验证码或用户判断，应请求用户协助；这不是“应用无法学习”。
- 后续新开 Codex 聊天执行用例、保存完整日志，并基于真实 `user_response`、events、
  metadata 和 learning / replay evidence 做两次复核：先判最终回复，再判过程日志。
- 最终 `wagent chat` 终端阶段性反馈由用户人工验收；本轮文档只定义验收点，不要求 Codex
  执行人工 smoke。

## 实现目标

本轮实现时至少应完成：

1. 定义 `active_task` metadata contract。
2. 新增 turn-based task reducer。
3. 在 learning 前增加 precondition guard。
4. 对未学过操作生成 learning confirmation，而不是冷拒绝。
5. 用户确认后能从 `awaiting_learning_confirmation` 继续。
6. 用户取消后清理 `active_task`。
7. learning failure 转成面客文案。
8. history 记录状态转移、precondition blocked、learning failure raw reason。
9. CLI / dispatch response 展示与真实阶段一致的用户反馈。
10. 先在文档中维护一轮对话评测用例矩阵，后续实跑时保存结果与完整日志供 Codex 复核。
11. 保持非 `interactive_chat` developer workflow 不变。

## 非目标

- 不做完整多页面 workflow。
- 不做 active browser tab。
- 不做 M12 recovery / retry / abort。
- 不做正式 risk / consent policy。
- 不做通用聊天系统。
- 不让 LLM 直接操作浏览器。
- 不让 LLM 输出 selector / browser steps / learned_path_id 作为执行授权。
- 不把 active_task 或 reducer 判断写入 LearnedPath proof。

## 待确认问题

1. 页面理解是否作为第一版必需前置：
   - 保守方案：只在缺目标 / 缺输入时辅助生成追问。
   - 激进方案：学习前必须 inspect / understand page。
2. `active_task` 的过期策略：
   - 建议按 turns_remaining 限制，例如 3 轮。

已收束决策：

- 学习成功后第一版不自动执行；必须先进入 `awaiting_execution_confirmation`。
- `active_task` 是 canonical task state，旧 pending state 只能作为兼容输入或派生状态。
- 第一版先用 `test-plan.md` 梳理一轮对话评测用例，后续实跑时保存结果与完整日志供 Codex 复核。

## 后续文档扩展

如果本需求确认通过，再扩展完整七件套：

- `intent.md`
- `contract.md`
- `technical-design.md`
- `plan.md`
- `review.md`

当前 `README.md` 和 `test-plan.md` 只用于确认需求、边界、评测预期和实现目标。
