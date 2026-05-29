# 11.3.8.5 · External Black-box Revalidation / Closeout

状态：NEEDS_USER_INPUT
里程碑：M11
类型：validation
父迭代：[`11.3.8-external-black-box-validation-recovery`](../11.3.8-external-black-box-validation-recovery/)
前置包：

- [`11.3.8.1-learning-action-goal-preservation`](../11.3.8.1-learning-action-goal-preservation/)
- [`11.3.8.2-suggested-utterance-generation`](../11.3.8.2-suggested-utterance-generation/)
- [`11.3.8.3-learned-action-matching-improvement`](../11.3.8.3-learned-action-matching-improvement/)
- [`11.3.8.4-regression-tests`](../11.3.8.4-regression-tests/)

## Iteration Type

- [ ] Documentation-only
- [ ] Code / tests
- [x] Validation / closeout

## Goal

通过 approved WAgent product surface 重跑 external black-box validation，并根据真实证据
把 `11.3.8` closeout 写成 `PASS`、`FAIL`、`FOLLOW_UP`、`BLOCKED` 或 `UNVERIFIED`。

## Current Status

当前包已创建，且已停在 live validation approval gate。必须先获得：

- API base URL；
- target URL；
- DB state cleaned or preserved；
- approved scenario list；
- 是否允许根据真实 evidence 更新 latest result docs。

未获得五项信息前，本包保持 `NEEDS_USER_INPUT`，不得运行 live validation。

## Scope

允许：

- 创建 validation / closeout package docs。
- 运行 pre-live read-only checks only after approval is available。
- 通过 approved `wagent chat` CLI / product UI surface 执行外部黑盒验证。
- 记录 operator actions、CLI raw product-client request / response records、
  `operator_actions` artifact、redacted JSON / Markdown artifacts，以及 stable
  latest redacted record at a stable repo path。
- 基于真实 evidence 更新 dated report 和 latest report。

禁止：

- 直接调用 autonomous-run endpoint。
- 用 direct replay API 或 internal service import 当 WAgent product pass evidence。
- 修改 runtime code/tests。
- 未经真实 revalidation 把 `PV-CLI-003` 或 11.3.8 写成 pass。

## Handoff

This package is blocked at the live validation approval gate.
