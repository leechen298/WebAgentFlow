# Codex 探索式验证提示词

本目录存放 Codex exploratory validation 的项目内置提示词和用例矩阵。

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
禁止 Codex 仅凭主观判断写“测试完成”。

## 当前矩阵

- Replay E2E 用例矩阵：`replay-e2e-cases.md`
- Replay E2E run prompt：`replay-e2e-run-prompt.md`

## 硬边界

Codex 探索式验证不能：

- 调用 `/exploration/autonomous-runs`。
- 调用 `/exploration/autonomous-runs/stream`。
- import 或直接运行 autonomous explorer。
- 依赖 LLM 服务。
- 修改产品代码。
- 修改 E2E spec 代码，除非后续任务明确要求。
- 新增 Skill / Superpowers / MCP 配置。
