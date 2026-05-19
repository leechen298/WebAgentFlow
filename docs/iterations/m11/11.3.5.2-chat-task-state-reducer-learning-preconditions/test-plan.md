# Test Plan

状态：draft_requirements

## 目标

本测试计划先定义 `wagent chat` / `wagent conversation send` 的面客回复评测用例。
当前阶段只写文档，不新增 `apps/cli/tests/test_conversation.py` 或其他自动化代码。

开发完成后，可以让一个评测 Agent 读取真实输入、`user_response`、conversation events、
session metadata、learning / replay result 和 browser operation evidence，判断实际回复是否
符合本文件预期。

本计划不把人工 `wagent chat` smoke 作为 Codex 本轮必跑项。最终用户使用的是
`wagent chat`，阶段性反馈的真实终端体验由用户在最终验收时人工确认。

## 评测原则

- 第一阶段先做一轮对话、多条 case；每条 case 只发送一条用户消息。
- 单条消息评测先校验最终 `user_response`，再校验同一轮产生的过程日志 / events。
- 回复不要求逐字匹配，但必须满足预期方向、必须包含项、禁止项和状态副作用。
- 对 URL 输入，系统不能只按“裸 URL -> 追问”处理；应先查询当前应用是否已有相关
  LearnedPath / learned action 记录，再决定询问、学习或执行。
- 没有学过时，系统可以自动启动学习，但必须在学习前和学习中持续做用户可理解的状态反馈。
- 学习失败不能直接变成“无法学习”。如果缺账号、密码、验证码、业务参数或用户判断，
  应判断为“需要用户协助 / 补充信息”，并给出下一步。
- 普通用户回复不得暴露内部错误、schema、provider raw error、trace、selector、Playwright
  step 或 learned_path_id。
- 本轮评测不触发 `verify-scenario`，不直接调用 autonomous-run endpoint。

## 验证层次

### L1：单条消息结果评测

入口可以是：

- first-run：通过 `wagent chat` 或等价 API flow 创建新的 `interactive_chat` session，并发送
  第一条用户消息。
- resume-send：通过 `wagent conversation send <session_id> --content <message>` 向指定
  历史会话发送一条消息。

评测顺序：

1. 先校验命令 / API 调用成功。
2. 再校验最终 `user_response`：
   - 非空。
   - 是正式 WAgent 回复，不是 transient progress。
   - 符合对应 case 的预期回复方向。
   - 不暴露内部错误、schema、provider raw error、selector、browser step 或 learned_path_id。
3. 最后校验本轮日志 / events / metadata 是否和最终回复一致。

### L2：过程日志 / events 评测

过程反馈可以通过日志最终校验，但必须是结构化、可关联的同一轮证据，不是散乱 stdout。

优先读取：

- conversation events。
- `progress_timeline` 或等价 structured progress events。
- session metadata 中的 `active_task`。
- learning result / replay result。
- page understanding summary。
- operation / browser evidence summary。

关联要求：

- 每条评测必须能通过 `session_id` 关联到会话。
- 如果系统能提供 `message_id` / `event_id` / `run_id`，评测 Agent 必须用它们收窄到同一轮
  用户输入，避免读取到旧日志。
- 如果缺少可关联证据，`user_response` 可以单独判定，但过程反馈判定应标为
  `needs_review` 或 `fail`，不能假定通过。

### L3：用户最终人工验证

最终用户使用的是 `wagent chat`。真实终端体验需要能看到阶段性反馈，例如：

- `正在查询是否已经学过这个页面`
- `正在打开页面`
- `正在理解页面内容和可操作目标`
- `正在学习这个页面的操作`
- `学习需要你补充必要信息`
- `学习完成，正在整理我学会了什么`

这层由用户最终人工验证。本文件只定义验收点，不要求 Codex 本轮执行人工 smoke。

## 评测输入 / 输出

评测 Agent 输入：

- `case_id`
- 用户发送的原始消息。
- 入口：first-run `wagent chat` 或 resume-send `wagent conversation send <session_id>`。
- dispatch response 的 `user_response`。
- conversation events。
- redacted session metadata。
- 如果触发 learning / replay：learning result、operation evidence、page understanding summary、
  recorded steps summary、failure reason。
- 关联字段：`session_id`，以及可用时的 `message_id`、`event_id`、`run_id`。

评测 Agent 输出：

```json
{
  "case_id": "C01",
  "status": "pass",
  "reason": "回复说明了能力边界，并引导用户提供页面地址。",
  "matched_expectations": ["non_empty_user_response", "mentions_web_learning"],
  "progress_checks": ["no_browser_action"],
  "violations": []
}
```

允许状态：

- `pass`：语义、状态副作用和禁止项都满足。
- `fail`：空回复、内部错误暴露、错误触发 browser / learning / replay、状态和回复不一致。
- `needs_review`：大方向正确，但措辞含糊、信息不完整或需要人工判断。

## 一轮对话用例

| Case | Entry | User message | Expected reply direction | Must include | Must not include | Expected state / side effect |
|---|---|---|---|---|---|---|
| C01 greeting | first-run | `你好` | 友好回复，说明 WAgent 可以学习网页操作、执行已学操作，并引导用户发页面地址或说明要做什么。 | “学习网页操作”或“执行已学操作”；“页面地址”或“要做什么” | 内部 Agent 名、schema、provider、`Learning run did not produce a LearnedPath` | 创建 `interactive_chat` session；不触发 browser / learning / replay；不创建 `active_task`。 |
| C02 capability | first-run or resume-send | `你能做什么？` | 说明产品边界：学习网页操作、执行已学操作、辅助查看/调试会话；引导用户提供 URL 和目标。 | “学习网页操作”；“执行已学操作”或“执行已经学会的操作”；“页面地址” | 通用聊天承诺；开放式闲聊续聊；provider raw error | 不触发 browser / learning / replay；不创建 `active_task`。 |
| C03 known URL | resume-send with existing learned action for URL | `http://localhost:5176/workspace-login` | 先查询应用是否已有该 URL / site scope 相关学习记录；如果已有，说明已学过相关操作，并询问用户想执行、复习还是重新学习什么。 | “我查到/找到已学过”；“你想让我做什么”或“要执行哪个操作” | 自动重复学习；直接执行；内部 learned_path_id | 不触发 replay，除非用户明确要求执行；可创建 `active_task.stage=learned_ready` 或保持轻量候选上下文。 |
| C04 unknown URL auto learn | first-run or resume-send with no learned action for URL | `http://localhost:5176/workspace-login` | 先查询记录；如果没有学过，应说明将尝试学习该页面，并开始学习。学习完成后，根据页面理解和操作记录报告学会了什么。 | “还没学过/没有找到已学记录”；“开始学习/我来学习”；学习成功时包含“学会了”以及页面/操作摘要 | 冷冰冰 no-path；只追问“要做什么”；内部错误 | 可进入 `learning`；学习成功后沉淀 LearnedPath，并回复 learned summary；不自动执行。 |
| C05 unknown URL needs user input | first-run or resume-send with no learned action for URL and page needs credentials | `http://localhost:5176/workspace-login` | 如果学习过程中发现需要账号、密码、验证码或用户判断，应说明需要用户协助，并明确要补充什么；这不是应用无法学习。 | “需要你提供/协助”；“账号/密码/验证码/必要信息”之一；“继续学习”或“取消” | `Learning run did not produce a LearnedPath`；“无法学习”；崩溃式错误 | 进入 `need_required_inputs` 或 `learning_failed` but recoverable；保留 `active_task`；不把缺信息当最终失败。 |
| C06 learning failed recoverable | resume-send | `学习 http://localhost:5176/workspace-login` | 如果学习未生成 LearnedPath，应根据页面理解和操作记录解释卡在哪里，并询问用户补充信息或确认下一步。 | “没有学成可复用路径/还没学成”；“可能需要”；“你可以补充/确认” | 直接展示 raw error；直接清空任务；笼统“失败”无下一步 | 记录 raw failure 到 history/debug；普通回复为可继续说明；保留或更新 `active_task.last_failure_reason`。 |
| C07 execute known action | resume-send with existing learned login action | `帮我执行 workspace-login 的登录` | 查询到已学操作后，可以说明将执行已学路径，或在需要确认时询问用户是否执行。 | “已学过/找到已学操作”；“执行”或“是否执行” | 跨 URL 误命中；重新学习；内部 learned_path_id | 可进入 `executing` 或 `awaiting_execution_confirmation`；不得跨 target URL / site origin 命中。 |
| C08 execute unknown action | resume-send with no learned action | `帮我执行 workspace-login 的登录` | 如果没有学过，应说明还没学过，并自动进入学习或询问是否先学习；不得直接 no-path 结束。 | “还没学过”；“先学习/现在学习” | 冷冰冰 no-path；直接执行；内部错误 | 进入 `learning` 或 `awaiting_learning_confirmation`；不触发 replay。 |
| C09 confirmation without task | first-run or empty session | `是` | 说明当前还不知道页面和操作目标，请用户先提供页面地址和要学习/执行的操作。 | “需要页面地址”或“还不知道要做什么”；“学习或执行的操作” | “开始学习”；“执行中”；browser action | 不触发 learning / replay；不创建可执行任务。 |
| C10 cancel without task | first-run or empty session | `取消` | 说明当前没有正在进行的网页任务，用户可以发页面地址重新开始。 | “没有正在进行”或“没有需要取消”；“页面地址” | 报错；内部 trace；browser action | 不触发 learning / replay；保持 `active_task` 为空。 |
| C11 unsupported non-web | first-run or resume-send | `帮我写一首诗` | 友好说明当前产品主要用于学习和执行网页操作，并引导回网页任务。 | “主要用于学习/执行网页操作”；“页面地址” | 长篇诗歌正文；开放式闲聊续聊；browser action | 不触发 browser / learning / replay；不创建 `active_task`。 |

## 过程日志期望

| Case group | Expected progress / log sequence | Required evidence |
|---|---|---|
| 问候 / 能力询问 / 非网页任务 | `message_received` -> `classifying_intent` -> `final_response_ready` | events 能证明未进入 browser / learning / replay。 |
| 已学 URL | `message_received` -> `classifying_intent` -> `collecting_context` -> `lookup_learned_actions` -> `final_response_ready` | learned action lookup 结果；未触发 replay。 |
| 未学 URL 自动学习 | `message_received` -> `classifying_intent` -> `collecting_context` -> `lookup_learned_actions` -> `opening_page` -> `understanding_page` -> `learning_operation` -> `learning_completed` 或 `learning_failed_recoverable` -> `final_response_ready` | page understanding summary、learning result、LearnedPath id 仅作为 debug/evidence，不进入普通回复。 |
| 学习需要用户输入 | `message_received` -> `opening_page` -> `understanding_page` -> `learning_operation` -> `waiting_for_user_input` -> `final_response_ready` | active_task 保留，missing input reason redacted；普通回复请求用户协助。 |
| 执行已学操作 | `message_received` -> `collecting_context` -> `lookup_learned_actions` -> `executing_learned_path` 或 `awaiting_execution_confirmation` -> `final_response_ready` | replay result 或确认态；不得跨 target scope 命中。 |

## URL 输入的判定分支

对于 `http://localhost:5176/workspace-login` 这类单独 URL 输入，评测 Agent 必须按以下分支判定：

1. 系统是否先查询当前 session / target scope 下的已学记录。
2. 如果已有记录：
   - 回复应说明已找到相关学习记录。
   - 应询问用户想执行哪个操作、是否重新学习、或下一步要做什么。
   - 不应直接重复学习或直接执行。
3. 如果没有记录：
   - 系统可以自动开始学习。
   - 学习期间应有用户可理解的阶段反馈。
   - 学习成功后必须报告“学会了什么”，并基于页面理解和操作记录生成摘要。
   - 学习成功后不自动执行，除非后续风险 / consent policy 明确允许。
4. 如果学习需要用户输入：
   - 回复应说明缺什么输入或需要什么协助。
   - 应保留可继续的 `active_task`。
   - 不得把缺输入当作应用无法学习。
5. 如果学习发生技术错误：
   - 普通回复应说明页面访问、浏览器、保存或系统问题，并给出下一步。
   - raw error 只能进 history / debug。

## Agent 判定重点

评测 Agent 不应做逐字匹配，应检查：

- 是否非空正式回复，而不是只有 progress。
- 是否符合 WAgent 产品边界。
- 是否先查已学记录再决定下一步。
- 是否根据 learned / unlearned / need-input / technical-error 分支给出不同回复。
- 是否把 learning failure 转成用户可理解、可继续的回复。
- 是否禁止暴露内部错误、schema、provider、selector、browser step、learned_path_id。
- 是否存在错误副作用：不该打开浏览器却打开、不该 replay 却 replay、不该清理任务却清理。

## 后续扩展

第一批一轮用例稳定后，再扩展多轮用例：

- URL -> 自动学习 -> 用户补充账号密码 -> 继续学习。
- URL 已学过 -> 用户说“执行” -> replay。
- 未学过执行目标 -> 自动学习 -> 学会后询问是否执行。
- 学习失败 recoverable -> 用户补充信息 -> 重试。
- 新 URL 覆盖旧 `active_task`。
- 取消后确认短句不再触发旧任务。
