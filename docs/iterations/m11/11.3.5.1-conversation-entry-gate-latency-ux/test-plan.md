# 测试计划（Test Plan）

状态：ready_for_implementation

## 适用条件

本轮涉及 Agent runtime、CLI UX、Conversation History trace 和跨层行为，因此必须维护
`test-plan.md`。

## 测试范围（Test Scope）

- Unit：Entry Gate schema、provider failure、classification result handling。
- Integration：ChatRuntime 在 Intake 前调用 Entry Gate；非网页输入跳过 Intake / Router。
- API：History detail 返回 Entry Gate trace / provenance。
- CLI：`wagent chat` 等待期间显示持续 working 状态；非 TTY fallback 不破坏输出。
- Console UI：如 history detail 页面展示新 trace，则补对应组件测试。
- E2E：不要求。
- Agent / Reporter / Recovery：只覆盖 Entry Gate / Router 边界，不涉及 recovery。
- Codex / AI External Operator：本轮文档阶段不要求。
- Live autonomous run：不运行。

## 测试矩阵（Test Matrix）

| ID | Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|---|
| GATE-1 | Unit | 非网页消息 | Entry Gate service test | `requires_agent_runtime=false`，不输出 skill / selector / step | Yes | 不用硬编码问候白名单 |
| GATE-1A | Unit | 闲聊 / 无关内容回复 | Orchestrator reply test | 快速友好回复，并引导用户提供 URL、学习页面操作或执行已学操作 | Yes | 不做开放式闲聊 |
| GATE-2 | Unit | 网页任务候选 | Entry Gate service test | `requires_agent_runtime=true` | Yes | URL、学习、执行、页面操作候选都应进入 runtime |
| GATE-3 | Unit | capability question | Entry Gate service test | category 为 `capability_question` 或等价结果 | Yes | 由 Orchestrator 生成统一能力说明 |
| NEG-1 | Unit | malformed JSON | provider fake | 不触发 learning / replay，记录 failure | Yes | fail closed |
| NEG-2 | Unit | low confidence | provider fake | 追问或友好说明，不触发 learning / replay | Yes | 不猜测执行 |
| NEG-3 | Unit | provider timeout / sleep | provider fake sleeps beyond timeout | 在硬超时内 fallback，不进入 Intake / Router / learning / replay | Yes | 目标 <=1500ms，硬上限 <=2000ms |
| CHAT-1 | Integration | Entry Gate 在 Intake 前执行 | ChatRuntime test | gate trace 早于 intake/router trace | Yes | 只限 interactive_chat |
| CHAT-2 | Integration | 非网页输入跳过重型 runtime | ChatRuntime test | Intake / Router provider fake 未被调用 | Yes | 返回友好回复 |
| CHAT-3 | Integration | 网页任务继续 11.3.5 flow | ChatRuntime test | Intake / Router 被调用 | Yes | 不破坏 11.3.5 |
| CLI-1 | CLI | TTY waiting UX | CLI unit / pty test | dispatch 等待期间有持续 spinner / working indicator | Yes | 不只是一行 `正在理解` |
| CLI-2 | CLI | non-TTY fallback | CLI unit | 无控制字符，输出可读 | Yes | CI 日志稳定 |
| CLI-3 | CLI | Ctrl-C cleanup | CLI unit / manual | spinner 不残留破碎行 | Recommended | 可自动化则自动化 |
| CLI-4 | CLI | agentic CLI interaction | CLI unit / pty test | progress 与最终 `WAgent >` 回复分离，等待期间不静默 | Yes | 参考 Codex CLI / Claude Code CLI 交互原则 |
| TRACE-1 | API | history trace | History API test | 返回 entry_gate category、latency、skipped_intake_router | Yes | redacted |
| TRACE-2 | API | provider thinking redaction | History API test | `<think>`、thinking、reasoning、chain_of_thought 不出现在 history/raw trace | Yes | 真实 trace 曾暴露该风险 |
| REG-1 | API/CLI | existing web task route | scoped chat tests | 既有 URL / 学习 / 执行路径仍通过 | Yes | 防止 gate 误拦 |

## Manual Smoke

实现完成后可由用户进行轻量手工试跑：

```bash
.venv/bin/wagent chat
```

观察项：

- 发送普通非网页消息时，CLI 快速回复，不出现长时间静默。
- 非网页 / 闲聊回复应把用户引导回 WebAgentFlow 的网页操作能力。
- 发送网页任务候选时，CLI 在等待期间持续显示 working 状态。
- 打开 history detail 能看到 Entry Gate trace。
- history detail / raw trace 不显示 provider thinking 或 chain-of-thought。

如果 Codex / AI 没有真实运行 CLI，不得写成 CLI smoke passed。

## E2E / UI Smoke 边界

- 本轮不要求真实浏览器 E2E。
- 不运行 `verify-scenario`。
- 不运行 autonomous run。
- 如果只跑单元测试 / API 测试 / CLI 测试，必须写明没有进行 live UI smoke。

## Live Run 边界

除非用户明确要求 live run，不得运行 `verify-scenario`、autonomous run 或 product-driven
browser execution。

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| Live autonomous run | 本轮优化 chat entry / CLI latency，不验证 autonomous exploration | 无 live evidence |
| Full product UI smoke | 不是文档阶段要求 | Console trace 展示需实现后补测 |
