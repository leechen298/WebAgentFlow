# 复盘 / 评审（Review）

状态：in_progress

## FINAL_STATUS

status: <PACKAGE_COMPLETE / REVIEW_READY / BLOCKED / FOLLOW_UP_REQUIRED / NEEDS_USER_INPUT / in_progress>
next_action: <exact next action>
parent_authorizes_runtime_implementation: <yes / no / N/A>
active_child_package: <child package id or N/A>
implementation_authorized: <yes / no / N/A>
do_not_start_next_package: <true / false / N/A>
blocking_findings: <none or list>
last_verified_at: <YYYY-MM-DD HH:MM TZ or N/A>
commands_run: <summary>
commands_not_run: <summary>

## <YYYY-MM-DD HH:MM> 设计评审（Design Review）

- Reviewer：
- Decision：approved | changes_requested | rejected
- Notes：

## <YYYY-MM-DD HH:MM> 代码评审（Code Review）

- Reviewer：
- Decision：approved | changes_requested | rejected
- Notes：

## 用户反馈

- <反馈> -> accepted | rejected，原因：<reason>

## 最终差异（Final Delta）

### 实际交付

- <实际交付内容。>

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- <偏差和原因，或 `None`。>

### WebAgentFlow Live Run 边界（Live Run Boundary）

除非用户明确要求 live run，不得触发 `verify-scenario`、autonomous run 或
product-driven browser execution。

如果用户明确要求 live run，必须记录：

- invocation surface；
- run_id；
- pass_gate.status；
- supervisor verdict；
- scorecard；
- 是 product UI traffic 还是 skill invocation；
- 原始输出或可复查路径。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 如果没有真实打开浏览器或产品 UI，不得声称完成 E2E / UI smoke。
- 如果没有真实运行 CLI / command，不得声称 CLI 已测试。
- 如果 Codex / AI 只是阅读代码、做静态推理或审查 diff，必须写成 review / inspection，
  不能写成 tested。
- 没有 run_id、截图、日志、exit code、pass / fail count 或可复查输出时，结论必须写成
  `not run` / `unverified`。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `<command or UI surface>` | `<expected>` | `<actual>` | `<0/1/... or N/A>` | `<counts>` | `<log / screenshot / run_id / output path>` | `<reason if failed/not run>` |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| <test item> | <why not run> | <risk or follow-up> |

### 后续事项（Follow-ups）

- <后续负责人 / 迭代，或 `None`。>
