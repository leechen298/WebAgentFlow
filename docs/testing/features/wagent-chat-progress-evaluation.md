# WAgent Chat Progress Evaluation

状态：draft

本文件定义 `wagent chat` / `wagent conversation send` 的面客回复与过程反馈评测方案。
它是长期测试域文档，不是某一次迭代的施工计划，也不是执行报告。

对应开发包：

- `docs/iterations/m11/11.3.5.2-chat-task-state-reducer-learning-preconditions/`

## 目标

验证 `wagent` 面向用户的一次消息处理是否同时满足：

1. 最终回复合理：`user_response` 能回答用户当前输入，不暴露内部错误。
2. 工作过程可解释：系统在查询、打开页面、理解页面、学习、需要用户协助、学习完成等阶段留下可关联日志。
3. 状态副作用正确：`active_task`、conversation events、learning / replay evidence 与最终回复一致。

本方案暂不设计独立的产品内自动判定模块。实际执行时，可以新开一个 Codex 聊天，由
Codex 跑用例、保存完整日志、先检查最终回复，再检查同一轮日志 / events。

## 验证层次

### L1：单条消息最终结果

入口可以是：

- first-run：通过 `wagent chat` 或等价 API flow 创建新的 `interactive_chat` session，并发送第一条消息。
- resume-send：通过 `wagent conversation send <session_id> --content <message>` 向指定历史会话发送一条消息。

检查顺序：

1. 命令 / API 调用成功。
2. `user_response` 非空。
3. `user_response` 是正式 WAgent 回复，不是 transient progress。
4. 回复语义符合用例预期。
5. 回复不暴露内部错误、schema、provider raw error、selector、browser step 或 `learned_path_id`。

### L2：同一轮过程日志 / events

工作过程反馈可以通过日志最终校验，但必须是结构化、可关联的同一轮证据。

优先读取：

- conversation events。
- `progress_timeline` 或等价 structured progress events。
- session metadata 中的 `active_task`。
- learning result / replay result。
- page understanding summary。
- operation / browser evidence summary。

关联要求：

- 每条评测必须记录 `session_id`。
- 如果系统能提供 `message_id` / `event_id` / `run_id`，必须用它们收窄到同一轮输入。
- 如果缺少可关联证据，最终回复可单独判定，但过程日志判定必须标为 `needs_review` 或
  `fail`，不能假定通过。

### L3：最终用户人工验证

最终用户使用的是 `wagent chat`。真实终端体验需要能看到阶段性反馈，例如：

- `正在查询是否已经学过这个页面`
- `正在打开页面`
- `正在理解页面内容和可操作目标`
- `正在学习这个页面的操作`
- `学习需要你补充必要信息`
- `学习完成，正在整理我学会了什么`

这层由用户最终人工验证。本文件只定义验收点，不要求 Codex 在文档阶段执行人工 smoke。

## 证据保存

每次实跑应保存一份人类可读结果到：

```text
docs/testing/results/YYYY-MM-DD-wagent-chat-progress-evaluation.md
```

每个 case 至少记录：

- `case_id`
- 执行入口：first-run / resume-send
- 用户消息
- 命令或 API 请求摘要
- `session_id`
- 可用时的 `message_id` / `event_id` / `run_id`
- 最终 `user_response`
- conversation events 摘要
- `active_task` 摘要
- learning / replay / page understanding 摘要（如果触发）
- 结果判定：final response check / process log check / overall
- 失败原因和下一步

示例记录结构：

```markdown
## C04 unknown URL auto learn

- Entry: resume-send
- Message: `https://example.invalid/app-entry`
- Session: `<session_id>`
- Message id: `<message_id or N/A>`
- Final response: ...
- Final response check: pass / fail / needs_review
- Process log check: pass / fail / needs_review
- Overall: pass / fail / needs_review

Events:

1. `message_received`
2. `collecting_context`
3. `lookup_learned_actions`
4. `opening_page`
5. `understanding_page`
6. `learning_operation`
7. `learning_completed`
8. `final_response_ready`

Notes:

- ...
```

## 用例矩阵

回复不要求逐字匹配，但必须满足预期方向、必须包含项、禁止项和状态副作用。

| Case | Entry | User message | Expected reply direction | Must include | Must not include | Expected state / side effect |
|---|---|---|---|---|---|---|
| C01 greeting | first-run | `你好` | 友好回复，说明 WAgent 可以学习网页操作、执行已学操作，并引导用户发页面地址或说明要做什么。 | “学习网页操作”或“执行已学操作”；“页面地址”或“要做什么” | 内部 Agent 名、schema、provider、`Learning run did not produce a LearnedPath` | 创建 `interactive_chat` session；不触发 browser / learning / replay；不创建 `active_task`。 |
| C02 capability | first-run or resume-send | `你能做什么？` | 说明产品边界：学习网页操作、执行已学操作、辅助查看/调试会话；引导用户提供 URL 和目标。 | “学习网页操作”；“执行已学操作”或“执行已经学会的操作”；“页面地址” | 通用聊天承诺；开放式闲聊续聊；provider raw error | 不触发 browser / learning / replay；不创建 `active_task`。 |
| C03 known URL | resume-send with existing learned action for URL | `https://example.invalid/app-entry` | 先查询应用是否已有该 URL / site scope 相关学习记录；如果已有，说明已学过相关操作，并询问用户想执行、复习还是重新学习什么。 | “我查到/找到已学过”；“你想让我做什么”或“要执行哪个操作” | 自动重复学习；直接执行；内部 `learned_path_id` | 不触发 replay，除非用户明确要求执行；可创建 `active_task.stage=learned_ready` 或保持轻量候选上下文。 |
| C04 unknown URL auto learn | first-run or resume-send with no learned action for URL | `https://example.invalid/app-entry` | 先查询记录；如果没有学过，应说明将尝试学习该页面，并开始学习。学习完成后，根据页面理解和操作记录报告学会了什么。 | “还没学过/没有找到已学记录”；“开始学习/我来学习”；学习成功时包含“学会了”以及页面/操作摘要 | 冷冰冰 no-path；只追问“要做什么”；内部错误 | 可进入 `learning`；学习成功后沉淀 LearnedPath，并回复 learned summary；不自动执行。 |
| C05 unknown URL needs user input | first-run or resume-send with no learned action for URL and page needs credentials | `https://example.invalid/app-entry` | 如果学习过程中发现需要账号、密码、验证码或用户判断，应说明需要用户协助，并明确要补充什么；这不是应用无法学习。 | “需要你提供/协助”；“账号/密码/验证码/必要信息”之一；“继续学习”或“取消” | `Learning run did not produce a LearnedPath`；“无法学习”；崩溃式错误 | 进入 `need_required_inputs` 或 recoverable `learning_failed`；保留 `active_task`；不把缺信息当最终失败。 |
| C06 learning failed recoverable | resume-send | `学习 https://example.invalid/app-entry` | 如果学习未生成 LearnedPath，应根据页面理解和操作记录解释卡在哪里，并询问用户补充信息或确认下一步。 | “没有学成可复用路径/还没学成”；“可能需要”；“你可以补充/确认” | 直接展示 raw error；直接清空任务；笼统“失败”无下一步 | 记录 raw failure 到 history/debug；普通回复为可继续说明；保留或更新 `active_task.last_failure_reason`。 |
| C07 execute known action | resume-send with existing learned login action | `帮我执行 sample-operation 的登录` | 查询到已学操作后，可以说明将执行已学路径，或在需要确认时询问用户是否执行。 | “已学过/找到已学操作”；“执行”或“是否执行” | 跨 URL 误命中；重新学习；内部 `learned_path_id` | 可进入 `executing` 或 `awaiting_execution_confirmation`；不得跨 target URL / site origin 命中。 |
| C08 execute unknown action | resume-send with no learned action | `帮我执行 sample-operation 的登录` | 如果没有学过，应说明还没学过，并自动进入学习或询问是否先学习；不得直接 no-path 结束。 | “还没学过”；“先学习/现在学习” | 冷冰冰 no-path；直接执行；内部错误 | 进入 `learning` 或 `awaiting_learning_confirmation`；不触发 replay。 |
| C09 confirmation without task | first-run or empty session | `是` | 说明当前还不知道页面和操作目标，请用户先提供页面地址和要学习/执行的操作。 | “需要页面地址”或“还不知道要做什么”；“学习或执行的操作” | “开始学习”；“执行中”；browser action | 不触发 learning / replay；不创建可执行任务。 |
| C10 cancel without task | first-run or empty session | `取消` | 说明当前没有正在进行的网页任务，用户可以发页面地址重新开始。 | “没有正在进行”或“没有需要取消”；“页面地址” | 报错；内部 trace；browser action | 不触发 learning / replay；保持 `active_task` 为空。 |
| C11 unsupported non-web | first-run or resume-send | `帮我写一首诗` | 友好说明当前产品主要用于学习和执行网页操作，并引导回网页任务。 | “主要用于学习/执行网页操作”；“页面地址” | 长篇诗歌正文；开放式闲聊续聊；browser action | 不触发 browser / learning / replay；不创建 `active_task`。 |

## 过程日志期望

| Case group | Expected progress / log sequence | Required evidence |
|---|---|---|
| 问候 / 能力询问 / 非网页任务 | `message_received` -> `classifying_intent` -> `final_response_ready` | events 能证明未进入 browser / learning / replay。 |
| 已学 URL | `message_received` -> `classifying_intent` -> `collecting_context` -> `lookup_learned_actions` -> `final_response_ready` | learned action lookup 结果；未触发 replay。 |
| 未学 URL 自动学习 | `message_received` -> `classifying_intent` -> `collecting_context` -> `lookup_learned_actions` -> `opening_page` -> `understanding_page` -> `learning_operation` -> `learning_completed` 或 `learning_failed_recoverable` -> `final_response_ready` | page understanding summary、learning result、LearnedPath id 仅作为 debug/evidence，不进入普通回复。 |
| 学习需要用户输入 | `message_received` -> `opening_page` -> `understanding_page` -> `learning_operation` -> `waiting_for_user_input` -> `final_response_ready` | `active_task` 保留，missing input reason redacted；普通回复请求用户协助。 |
| 执行已学操作 | `message_received` -> `collecting_context` -> `lookup_learned_actions` -> `executing_learned_path` 或 `awaiting_execution_confirmation` -> `final_response_ready` | replay result 或确认态；不得跨 target scope 命中。 |

## URL 输入的判定分支

对于 `https://example.invalid/app-entry` 这类单独 URL 输入，检查以下分支：

1. 系统是否先查询当前 session / target scope 下的已学记录。
2. 如果已有记录：
   - 回复应说明已找到相关学习记录。
   - 应询问用户想执行哪个操作、是否重新学习、或下一步要做什么。
   - 不应直接重复学习或直接执行。
3. 如果没有记录：
   - 系统可以自动开始学习。
   - 学习期间应有用户可理解的阶段反馈。
   - 学习成功后必须报告“学会了什么”，并基于页面理解和操作记录生成摘要。
   - 学习成功后不自动执行，除非后续 risk / consent policy 明确允许。
4. 如果学习需要用户输入：
   - 回复应说明缺什么输入或需要什么协助。
   - 应保留可继续的 `active_task`。
   - 不得把缺输入当作应用无法学习。
5. 如果学习发生技术错误：
   - 普通回复应说明页面访问、浏览器、保存或系统问题，并给出下一步。
   - raw error 只能进 history / debug。

## Codex 实跑流程

后续新开 Codex 聊天执行时，按以下顺序：

1. 确认项目服务、数据库和目标测试页面可用。
2. 对每个 case 建立或复用明确的 `interactive_chat` session。
3. 发送一条用户消息。
4. 保存最终 `user_response`。
5. 读取同一轮 conversation events / history / metadata / learning evidence。
6. 将结果写入 `docs/testing/results/YYYY-MM-DD-wagent-chat-progress-evaluation.md`。
7. 先判最终回复，再判过程日志，最后给出 overall。

## 后续扩展

第一批一轮用例稳定后，再扩展多轮用例：

- URL -> 自动学习 -> 用户补充账号密码 -> 继续学习。
- URL 已学过 -> 用户说“执行” -> replay。
- 未学过执行目标 -> 自动学习 -> 学会后询问是否执行。
- 学习失败 recoverable -> 用户补充信息 -> 重试。
- 新 URL 覆盖旧 `active_task`。
- 取消后确认短句不再触发旧任务。
