# 12.2 User Abort / Stop Handling Intent

Status: documentation initialized.

## Goal

初始化 12.2 文档边界：定义当用户明确发出 abort / stop 信号时，
WebAgentFlow 如何保护用户控制权、停止继续操作、记录当时证据，并把后续选择
交给后续 M12 包。

12.2 是 user abort / stop handling boundary，不是恢复执行器。

## Motivation

M12 不能只处理 engine failure。真实运行时还会出现另一类更高优先级信号：用户
主动叫停。这个信号的含义不是“系统失败”，而是“用户收回控制权”。

如果把 abort 混入 12.1 failure classification，会出现两个风险：

- 系统可能把用户叫停误报成 engine failure；
- 系统可能在 failure recovery 逻辑里继续生成 proposal、retry suggestion 或
  browser continuation，从而违背用户叫停意图。

如果 12.2 直接跳到 12.3 proposal 或 12.4 retry policy，也会让 abort 后的
第一步不清楚：系统还没明确停止边界，就开始讨论如何恢复。M12 必须先定义
“收手”规则，再谈后续选择。

## Boundary / Non-goals

12.2 做：

- user abort signal semantics；
- stop / pause boundary；
- abort evidence capture；
- abort acknowledgement；
- no-new-browser-action rule；
- in-flight execution caveat；
- abort vs failure distinction；
- abort vs pause / cancel / takeover distinction；
- idempotent abort handling；
- handoff boundary to later recovery choices；
- future test plan。

12.2 不做：

- failure classification changes；
- recovery proposal generation；
- retry / re-run policy；
- retry execution；
- replan execution；
- conversation recovery flow；
- teaching mode；
- takeover implementation；
- LearnedPath write-back；
- M11.2 Runtime Observation / Wait-for-change；
- API endpoint；
- CLI command；
- database migration；
- frontend UI；
- E2E；
- `verify-scenario`。

## Success Criteria

- 文档明确 user abort 是用户控制权信号，不是 engine failure。
- 文档明确 abort accepted 后不得继续新的浏览器动作。
- 文档说明 in-flight action 只能 best-effort stop，不能承诺撤销已发生的外部
  副作用。
- 文档区分 abort / stop、pause、cancel、takeover。
- 文档定义重复 abort / stop 的幂等处理要求。
- 文档定义 interruption time evidence capture 要求。
- 文档明确 12.2 不生成 proposal、不执行 retry、不接 conversation recovery flow。
- M12 README / m12-plan 已加入 12.2，并保持 12.3 / 12.4 / 12.5 为 future package。
