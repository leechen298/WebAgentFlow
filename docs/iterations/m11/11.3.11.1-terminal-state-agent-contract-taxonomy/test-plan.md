# 测试计划（Test Plan）

状态：proposed

## 适用条件

本包涉及 Agent 边界、product-model update、evidence semantics、future schema direction 和
campaign route，因此必须维护 `test-plan.md`。默认验证是 docs integrity / design review；
不运行 runtime tests 或 live autonomous validation。

## 测试范围（Test Scope）

- Unit：N/A。本包不改 runtime code。
- Integration：N/A。本包不改 service integration。
- API：N/A。本包不改 API。
- Console UI：N/A。本包不改 UI。
- E2E：N/A。本包不打开浏览器。
- Agent / Reporter / Recovery：docs review only；验证 Agent role boundary 是否清楚。
- Codex / AI External Operator：docs integrity commands only。
- Live autonomous run：not run；父包和本包均未授权。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Docs integrity | Child seven-document set exists | `find docs/iterations/m11/11.3.11.1-terminal-state-agent-contract-taxonomy -maxdepth 1 -type f -print | sort` | README / intent / contract / technical-design / test-plan / plan / review present | Yes | No runtime |
| Product model | Terminal-state evidence contract aligned with L1 | `rg -n "terminal-state|Terminal State Agent|no legacy alias" docs/product-model.md` | L1 handoff and no-Agent-I boundary discoverable | Yes | No new letter |
| Roadmap/index | Child route discoverable | `rg -n "11\\.3\\.11\\.1|Terminal State Agent" docs/roadmap.md docs/iterations/m11/README.md` | M11.3 post-closeout and child route visible | Yes | M14 reuse only |
| Template hygiene | No template residue | `rg -n "T[B]D|T[O]DO" ...` | No matches in touched docs | Yes | Avoid empty docs |
| Diff hygiene | Whitespace clean | `git diff --check` | Exit 0 | Yes | Whole repo diff hygiene |

## Product Model Alignment Review

Required review questions:

- Does terminal-state classification belong to L1 autonomous learning?
- Does it sit after code-driven attempt execution and before Attempt Evaluation?
- Does product model preserve Page Understanding Agent, Attempt Evaluation Agent and Learning Report Agent as separate roles?
- If Terminal State Agent naming is used, is legacy alias explicitly `no legacy alias`?
- Does the document avoid implying LLM-controlled per-step browser execution?

## Roadmap / M11 Index Review

Required review questions:

- Is 11.3.11 described as M11.3 post-closeout stop-control work, not M14 implementation?
- Is future M14 reuse described without claiming M14 completion?
- Is child 1 listed or discoverable as the active child?

## E2E / UI Smoke 边界

No UI smoke or browser E2E is part of this child package. If no browser was opened, final review must say
`not run` for UI smoke / E2E.

## Codex / AI 外部测试操作员边界

Codex may run docs integrity shell commands only. It must not claim product behavior is validated.

## Live Run 边界

Default status: `not_run`.

Do not run `verify-scenario`, product UI live smoke, or autonomous-run endpoints. This child has no target URL,
scenario list, result-doc update scope, or user live-run approval.

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| Runtime unit tests | No runtime code changed | Runtime implementation starts in later child packages |
| API / service tests | No API/service changed | None for this docs package |
| Console / CLI tests | No Console/CLI changed | None for this docs package |
| Browser E2E / UI smoke | Not in scope | Terminal behavior remains unverified until later child validation |
| Live autonomous validation | Not authorized and not in scope | No `run_id` / `pass_gate.status` claim |
