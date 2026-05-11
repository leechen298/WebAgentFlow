# Exploratory Testing 提示词

本目录存放 exploratory validation 的项目内置提示词和用例矩阵。

当前已建立的探索式验证只针对 M10.2 Replay 测试域。它是第二阶段测试工作流，
不能替代 deterministic E2E，也不是 WebAgentFlow 全项目自动测试。

## 报告要求

所有探索式验证报告必须写到 `docs/testing/results/`。

报告必须是证据型报告：

- 写清测了什么。
- 写清怎么测的。
- 写清实际运行了哪些命令。
- 写清命令退出码。
- 摘录真实 stdout/stderr。
- 写清哪些没跑。
- 写清哪些阻塞。

PASS 必须有命令或浏览器操作证据。没有证据只能写 `NOT_RUN` 或 `BLOCKED`。
禁止任何执行 Agent 仅凭主观判断写“测试完成”。

## 证据类型

探索式验证报告必须区分：

- deterministic E2E：Playwright Test 自动化回归，通常 headless。
- API exploratory：直接 API 调用，并保留命令、退出码和响应摘录。
- Agent-operated UI exploratory：Codex、Claude Code 或其他具备浏览器能力的
  Agent，或 headed Playwright，打开真实页面，执行可见 UI 操作。

Headless E2E 不能算 Agent-operated UI exploratory。API-only 调用不能算
Agent-operated UI exploratory。UI PASS 必须包含页面观察、截图、trace、video 或
明确的 browser observation 证据。

## 当前矩阵

- Replay E2E 用例矩阵：`replay-e2e-cases.md`
- Replay E2E run prompt：`replay-e2e-run-prompt.md`
- Replay visual UI run prompt：`replay-visual-ui-run-prompt.md`

## 硬边界

探索式验证不能：

- 调用 `/exploration/autonomous-runs`。
- 调用 `/exploration/autonomous-runs/stream`。
- import 或直接运行 autonomous explorer。
- 依赖 LLM 服务。
- 修改产品代码。
- 修改 E2E spec 代码，除非后续任务明确要求。
- 新增 Skill / Superpowers / MCP 配置。
