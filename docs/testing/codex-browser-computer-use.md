# Codex Browser / Computer Use 兼容入口

本文件保留为历史链接兼容入口。

原先这里维护 “Codex 使用 Browser Use / Computer Use 自己操作网页” 的测试规程。
现在这类测试已改为工具无关的 **Agent-operated UI Exploratory**
（Agent 可视化页面探索测试）。

请阅读：

- `docs/testing/agent-operated-ui/README.md`

当前口径：

- Codex 只是可选执行工具之一。
- Claude Code、其他带 Browser Use / Computer Use 能力的 Agent、headed Playwright
  也可以按同一份用例和报告模板执行。
- 重点是用例、真实页面操作、可见 UI 观察和证据报告，不是工具名字。

本文件不再维护重复用例。新增 Agent-operated UI exploratory 用例和报告模板应写入
`agent-operated-ui/README.md`。
