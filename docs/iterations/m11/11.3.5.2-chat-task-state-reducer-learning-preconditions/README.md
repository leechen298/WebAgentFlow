# 11.3.5.2 · Chat Task State Reducer & Learning Preconditions

状态：draft_requirements
里程碑：M11
类型：code
父迭代：11.3.5 · Customer-Facing Agent Router & Skill Runtime
前置相关：11.3.5.1 · Conversation Entry Gate & Chat Latency UX

## 一句话目标

把 `wagent chat` 从“每轮按单句意图直接 learn / execute”升级为“每轮根据当前输入和会话状态推导下一步”的任务状态推进入口；在学习前守住必要前置条件，并把学习失败转成用户能理解、能继续操作的反馈。

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
+ active_task
+ pending_target / pending_intake
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

示例结构：

```json
{
  "active_task": {
    "target_url": "<target-url>",
    "target_source": "user_message_url",
    "goal": null,
    "canonical_goal": null,
    "slots": [],
    "stage": "target_collected",
    "proposed_next_action": "ask_operation_goal",
    "last_failure_reason": null,
    "turns_remaining": 3
  }
}
```

原则：

- `active_task` 是代码侧状态，不是 LLM 记忆。
- LLM 可以帮助理解用户输入，但不能直接决定状态转移是否生效。
- Orchestrator / reducer 负责合并用户输入、校验 scope、更新 stage、调用 skill。
- `active_task` 只能记录 conversation / task state，不得写成 LearnedPath evidence。

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
| `learned_ready` | 已学会，可执行 | 执行或提示后续说法 |
| `executing` | 正在执行已学路径 | 记录 progress，等待 replay result |
| `done` | 本轮任务完成 | 保留摘要或清理 active task |
| `blocked` | 当前不支持或信息不足无法继续 | 给出下一步建议 |

状态命名可以在技术设计阶段微调，但必须保留“每轮 reducer 推进”的语义。

## 学习前置条件

`start_learning` 前必须满足：

1. `target_url` 明确。
2. `goal` / `canonical_goal` 明确。
3. 必要输入齐全，或页面 / 操作被确认不需要输入。
4. 当前任务处于可学习 stage。
5. 不依赖 validation spec / assertions oracle 补输入。

如果缺任何一项，不得启动 learning，不得打开浏览器执行学习动作。

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
- 应生成 `awaiting_learning_confirmation`。
- 用户可通过确认类回复继续，例如“是”“可以”“学习”。
- 用户可通过取消类回复终止，例如“取消”“不用了”。

建议用户反馈：

```text
我还没学过这个页面上的这个操作。要我现在学习吗？回复“是”开始学习，回复“取消”停止。
```

### 学习后是否自动执行

如果用户原始目标是执行，并且系统为了执行而学习：

- learning 成功后可以进入 `learned_ready`。
- 是否自动执行由 reducer / Orchestrator 根据当前任务上下文决定。
- 第一版可以采用保守策略：学习完成后询问是否执行；如果文档审核确认低影响 happy path 可自动执行，再在技术设计中写明条件。

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

如果暂时不做 streaming，最终 response 至少应携带面客化阶段摘要，避免浏览器已打开但用户仍只看到“正在理解”。

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

### 输入学习 + URL，但缺操作目标

不启动 learning，先追问：

```text
我看到了这个页面地址。你想让我学习这个页面上的什么操作？请补充要学习的操作和需要填写的信息。
```

### 输入取消

清理当前 `active_task`：

```text
好的，已取消这次操作。
```

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
10. 保持非 `interactive_chat` developer workflow 不变。

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

1. 学习成功后是否自动执行：
   - 保守方案：先询问用户是否执行。
   - 激进方案：如果原始目标是执行、信息完整、低影响，则学习后自动执行。
2. 页面理解是否作为第一版必需前置：
   - 保守方案：只在缺目标 / 缺输入时辅助生成追问。
   - 激进方案：学习前必须 inspect / understand page。
3. `active_task` 的过期策略：
   - 建议按 turns_remaining 限制，例如 3 轮。

## 后续文档扩展

如果本需求确认通过，再扩展完整七件套：

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`

当前文件只用于确认需求、边界和实现目标。
