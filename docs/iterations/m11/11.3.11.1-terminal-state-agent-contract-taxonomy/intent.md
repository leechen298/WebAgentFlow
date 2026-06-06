# 意图（Intent）

状态：proposed

## 目标

把 `Terminal State Agent / 终态判断 Agent` 从父包的 proposed route 收敛为可评审的
M11.3.11 scoped L1 evaluator worker / terminal evidence contract，使后续 browser event
recorder、Page Understanding terminal hints、stop control、Attempt Evaluation ingest gate
可以按同一套 taxonomy 和证据语义实现。

## 动机

11.3.10 已经让 URL-only learning 能拆解筛选控件和 capability scenario，但仍暴露一个更底层问题：
一次 attempt 何时结束、结束后证据强弱如何判断、能否停止等待并交给 Attempt Evaluation，
当前系统没有统一契约。

如果不先定义终态 taxonomy 和 Agent 边界，后续实现很容易滑向：

- 把 `/users`、字段文案或 DOM id 写入 runtime 规则。
- 用 click 后截图差异替代 browser / network / DOM / region / Page Understanding 证据。
- 把 failed / unverified attempt 沉淀为成功 LearnedPath。
- 让 Terminal State Agent 替代 Attempt Evaluation Agent 或直接控制浏览器步骤。

## 边界 / 非目标

- 不实现 browser event recorder、Terminal State Agent runner、stop controller 或 LearnedPath ingest gate。
- 不运行 `verify-scenario`、autonomous run、product UI smoke 或任何 live validation。
- 不新增 legacy Agent 字母，不改变 L1 / L2 / L3 lifecycle stages。
- 不把完整 M14 Learning Quality / Coverage / Negative Knowledge 提前实现。

## 成功标准

- 子包七件套存在且无模板残留。
- `docs/product-model.md` 明确 terminal-state classification 位于 code-driven attempt trial 和 Attempt Evaluation Agent 之间；如使用 Terminal State Agent 命名，必须标注 `no legacy alias` 且不新增 legacy Agent letter。
- `docs/roadmap.md` 说明 11.3.11 是 M11.3 post-closeout stop-control follow-up，未来 M14 可复用其 evidence contract。
- `contract.md` 定义 terminal types、terminal outcomes、evidence strength、stop decisions、redaction、storage 方向和 child implementation gates。
- `review.md` 记录设计复核结论、implementation authorization 状态、实际执行的 docs integrity checks 和未运行项。
