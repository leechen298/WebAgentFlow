# 测试计划（Test Plan）

状态：PACKAGE_COMPLETE

## 测试范围

- Unit：terminal-state classifier and schema.
- Integration：optional autonomous result metadata wiring.
- Live autonomous run：not run.

## 测试矩阵

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Unit | download event | pytest terminal state | detected/download/strong/stop | Yes | Synthetic timeline |
| Unit | dialog/popup event | pytest terminal state | detected modal/dialog stop | Yes | Synthetic timeline |
| Unit | navigation event + hint | pytest terminal state | detected navigation stop | Yes | Synthetic timeline |
| Unit | list refresh/network completion | pytest terminal state | detected list/network stop | Yes | Synthetic timeline + hints |
| Unit | request-only pending | pytest terminal state | not_terminal_yet/network/wait | Yes | No response yet |
| Unit | request-only max wait | pytest terminal state | terminal_unverified/network/unverified_stop | Yes | Metadata only |
| Unit | requestfailed/pageerror | pytest terminal state | terminal_failed/unverified_stop | Yes | Synthetic timeline |
| Unit | missing evidence | pytest terminal state | terminal_unverified/continue | Yes | Safety |
| Unit | recorder unavailable | pytest terminal state | terminal_unverified/unverified_stop | Yes | Safety |
| Boundary | no selectors/secret values | pytest terminal state | output has ids/summaries only | Yes | Redacted input assumed |

## Live Run 边界

Do not run `verify-scenario`, autonomous run, product UI smoke or direct autonomous endpoints.

## 未运行项

| Item | Reason | Risk |
|---|---|---|
| Live autonomous validation | Not authorized | No run_id/pass_gate proof |
| Provider-backed Agent review | First version deterministic | LLM-backed wording remains future work |
