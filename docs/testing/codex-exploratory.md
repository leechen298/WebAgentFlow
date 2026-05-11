# Exploratory Testing

探索式验证是第二阶段测试工作流，不能替代确定性 E2E 回归。

它的目标是让 AI coding agent 阅读产品和 API contract，提出边界用例，运行本地
确定性 E2E，观察 console 和 validation-site，并识别后续应该沉淀为长期测试的缺口。

当前第一批探索式验证只针对 M10.2 replay 测试域，不是 WebAgentFlow
全项目自动测试。后续如果 conversation、task-execution、recovery、teaching、
multi-page-workflow 等能力进入实现，应分别建立各自的用例矩阵。

Replay 探索式验证资料位于：

- `docs/testing/exploratory/replay-e2e-cases.md`
- `docs/testing/exploratory/replay-e2e-run-prompt.md`
- `docs/testing/exploratory/replay-visual-ui-run-prompt.md`

确定性 E2E 轨道见 `docs/testing/e2e/README.md`。Agent-operated UI exploratory
规程见 `docs/testing/agent-operated-ui/README.md`。

## 证据边界

探索式验证必须明确证据类型：

- deterministic E2E：自动化回归证据，通常 headless。
- API exploratory：API-only 命令证据。
- Agent-operated UI exploratory：Codex、Claude Code 或其他具备浏览器能力的
  Agent，或 headed Playwright，打开真实页面并执行可见 UI 操作。

Headless Playwright E2E 不能算 Agent-operated UI exploratory。API-only 调用也
不能算 Agent-operated UI exploratory。若没有页面观察、截图、trace、video 或明确
browser observation 证据，UI case 不能写成 Agent-operated UI exploratory PASS。

## 硬边界

探索式验证不能：

- 调用 `/exploration/autonomous-runs`。
- 调用 `/exploration/autonomous-runs/stream`。
- import 或直接运行 autonomous explorer。
- 依赖 LLM 服务。

## 允许的活动

探索式验证可以：

- 运行确定性 E2E 套件。
- 使用 headed Playwright 查看本地 console 和 validation-site。
- 提出新的确定性 E2E 用例。
- 把稳定发现转成长期 Playwright Test 用例。

当前测试基础设施阶段不实现自动探索脚本。
