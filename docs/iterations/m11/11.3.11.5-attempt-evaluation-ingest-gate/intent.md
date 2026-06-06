# 意图（Intent）

状态：PACKAGE_COMPLETE

## 背景

Child 4 已提供 advisory `TerminalStateVerdict`，说明 attempt 是否达到可评价终态以及停止/等待建议。
但这仍然不是 LearnedPath 成功证明。当前 ingest 路径主要依赖 existing `pass_gate.status == pass`
和 steps trimming；child 5 需要补上 terminal-state evidence gate，避免“只点击按钮”或证据不足的
attempt 被记录为成功 LearnedPath。

## 目标

- 定义 attempt evaluation / ingest gate 的最小 schema 和规则。
- 让 LearnedPath ingest 只接受 `terminal_detected` 且 evidence 足够、且 existing pass gate 为 `pass`
  的 attempt。
- 让 `terminal_unverified`、`not_terminal_yet`、`terminal_failed` 明确不可进入成功 LearnedPath。
- 保留失败 / unverified 的可审计摘要，供后续 child 6 展示或未来 negative knowledge 使用。

## 非目标

- 不实现 LLM-backed Attempt Evaluation prompt。
- 不改 Supervisor / pass_gate 计算。
- 不新增数据库表或 migration。
- 不运行 live autonomous validation。
- 不做 Console / CLI 展示。

## 成功标准

- 纯函数或 service tests 覆盖 success / unverified / failed / no terminal evidence。
- Existing pass gate 仍是必须条件，不被 terminal verdict 绕过。
- Failed / unverified attempt 不会生成成功 LearnedPath。
