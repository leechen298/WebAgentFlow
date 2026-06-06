# 测试计划（Test Plan）

状态：proposed

## 适用条件

本包修改 browser runtime evidence、redaction、event metadata 和 autonomous exploration integration，
必须有 `test-plan.md`。默认测试是 non-live unit/integration；不运行 `verify-scenario`、autonomous
live run 或 product UI smoke。

## 测试范围（Test Scope）

- Unit：browser event conversion, redaction, bounded timeline, status derivation.
- Integration：recorder hook into autonomous run metadata if implementation touches runtime.
- API：N/A by default; child 6 owns read model.
- Console UI：N/A.
- E2E：N/A by default.
- Agent / Reporter / Recovery：N/A; no Agent prompt changes.
- Codex / AI External Operator：shell commands only.
- Live autonomous run：not run.

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Unit | request/response/requestfailed event conversion | pytest recorder tests | Safe metadata, no body | Yes | Synthetic event objects |
| Unit | download/dialog/popup/navigation/load/console/pageerror conversion | pytest recorder tests | Event type and bounded metadata | Yes | No live browser required |
| Unit | URL/header/message/filename redaction | pytest recorder tests | tokens/cookies/auth/body/direct PII removed | Yes | Include warnings |
| Unit | bounded timeline truncation | pytest recorder tests | deterministic truncation and count | Yes | No unbounded memory |
| Unit | correlation ids | pytest recorder tests | correlation_id plus attempt/action/step ids present when bound | Yes | run_id may be attached only after persistence |
| Unit | failure status derivation | pytest recorder tests | available/partial/unavailable statuses | Yes | Recorder errors non-fatal |
| Integration | autonomous metadata includes optional timeline | targeted existing test or new integration test | old flow still works | Yes if runtime hook implemented | Non-live mocks |
| Static | lint / import check | ruff | no lint/import errors | Yes | Changed files only |
| Hygiene | whitespace | `git diff --check` | no whitespace errors | Yes | Whole repo diff |

## Redaction Required Cases

- `Authorization` header.
- `Cookie` / `Set-Cookie` header.
- URL query keys such as `token`, `access_token`, `id_token`, `code`, `secret`, `password`, `session`.
- Request body and response body are not stored.
- Email / phone / ID-like direct personal data in dialog or console text should be bounded and redacted when detected.
- Download filename should remove path separators and control characters.
- WebAgentFlow private fields such as `selector`, `target_selector`, `slot_overrides`, `pending_choice_private_map`,
  `evidence_targets`, and raw `learned_path_id` must not be exposed as public terminal evidence.

## E2E / UI Smoke 边界

No browser E2E or UI smoke is required for child 2 default verification. If a later implementation uses a controlled
Playwright page test, it must be recorded as controlled-browser test, not live autonomous validation.

Preferred default is fake page/context event emitters or direct synthetic event objects, following existing mock-heavy
patterns in wait-for-change and action-executor tests. Do not start a real Playwright browser unless implementation
review explicitly scopes a controlled-browser test.

## Codex / AI 外部测试操作员边界

Codex may run unit/integration/static commands. It must not call autonomous-run endpoints directly and must not present
synthetic event tests as product live proof.

## Live Run 边界

Default status: `not_run`.

Live autonomous validation requires explicit user approval with target, scenario, surface and result-doc update scope.

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| `verify-scenario` | Not in default scope | No run_id/pass_gate proof |
| Product UI smoke | Not in default scope | Event capture not visually validated |
| Live autonomous validation | Not authorized | Real target evidence remains future work |
| Console evidence rendering | Child 6 owns UI | Event timeline may be internal until later |
