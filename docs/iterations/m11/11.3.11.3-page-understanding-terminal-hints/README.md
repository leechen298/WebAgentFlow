# 11.3.11.3 Page Understanding Terminal Hints

状态：REVIEW_READY
里程碑：M11.3 post-closeout
类型：code / mixed
父包：`11.3.11-terminal-state-agent-learning-stop-control`
前置子包：`11.3.11.1-terminal-state-agent-contract-taxonomy`, `11.3.11.2-browser-event-recorder`

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

本包为 terminal-state 判断提供 Page Understanding terminal hints：页面用途、内容摘要、区域、
可能功能、控件到区域的提示和候选终态类型。第一版采用 deterministic PageAnalysis bridge，
不接 live LLM provider，不输出 selectors / raw DOM paths，不控制浏览器。

## 文档集

- `README.md` - 包索引、状态、依赖和门禁。
- `intent.md` - 目标、动机、边界和成功标准。
- `contract.md` - PageTerminalHint schema、候选终态和边界契约。
- `technical-design.md` - deterministic bridge、schema、数据流和测试入口。
- `test-plan.md` - synthetic PageAnalysis tests、boundary tests、compatibility tests。
- `plan.md` - 实施步骤、allowed / forbidden files、验证命令。
- `review.md` - design review、implementation authorization 和最终验证证据。

## 当前状态

本包七件套已生成并进入 design review。Runtime implementation 只有在 `review.md` 记录
`implementation_authorized: yes` 后才能开始。
