# 复盘 / 评审（Review）

状态：completed_after_fix_rerun（final closeout rerun pass）

## Current Decision

- Reviewer：ChatGPT
- Decision：completed_after_fix_rerun
- Code：not_changed_in_this_package
- Live eval：pass
- Notes：
  - 本包只定义 11.3.6 closeout sweep，不修改 runner 或 runtime。
  - blocked artifact 只能证明 blocked 被记录；不得把 blocked 写成 completed /
    `closed_live` / `closed_non_live`。
  - First sweep returned exit `2` for both required evals because API health was unavailable.
  - Service-available rerun returned exit `1` for both required evals because required gates
    failed.
  - 11.3.6.6 fixes landed; final rerun returned exit `0` for items, failure recovery,
    pending choice, and planner choice.

## 初始复核记录

- 2026-05-23 已对齐 `origin/v0.1`。
- 当前 HEAD：`8ef8b2b Close out planner-backed choice eval docs`。
- 工作区：clean。
- Runner 代码已包含 `SCHEMA_VERSION = "11.3.6.4"` 和 11.3.6.3 / 11.3.6.4 case。
- `package.json` 已包含：
  - `eval:wagent:pending-choice`
  - `eval:wagent:planner-choice`
- `docs/testing/results/` 当前只有 11.3.6.1 / 11.3.6.2 result。
- `artifacts/wagent-eval/` 当前只有 11.3.6.1 / 11.3.6.2 JSON artifact。
- 11.3.6.3 / 11.3.6.4 review 仍显示 `Code: not_started` / `Live eval: not_run`。

## 设计评审收口

- 11.3.6.5 作为 docs / verification closeout 包通过。
- 11.3.6.3 / 11.3.6.4 可按实际结果记录 live / non-live / blocked；未跑 live 时不得写
  live pass。
- 如果服务不可用，允许提交 blocked artifact 作为 blocked evidence，但对应子包不得写
  `implementation_complete_non_live` 或 `implemented_and_live_eval_passed`。
- Program status 在存在 required blocked 子包时不得写 `closed_live` 或 `closed_non_live`。

## 2026-05-23 Closeout Sweep

| Command / Surface | Expected | Actual result | Exit code | Status | Evidence | Notes |
|---|---|---|---:|---|---|---|
| `git rev-parse --short HEAD` | current commit recorded | `51967a7` | 0 | Pass | command output | first closeout-ready commit |
| `pnpm run eval:wagent:pending-choice` | pass or blocked artifact | `status=blocked`; artifact written | 2 | Blocked | `artifacts/wagent-eval/wagent-runtime-eval-20260523T093605Z.json`; `docs/testing/results/m11-11.3.6.3-pending-choice-multi-candidate-eval-20260523T093605Z.md` | API health unavailable |
| `pnpm run eval:wagent:planner-choice` | pass or blocked artifact | `status=blocked`; artifact written | 2 | Blocked | `artifacts/wagent-eval/wagent-runtime-eval-20260523T093610Z.json`; `docs/testing/results/m11-11.3.6.4-planner-backed-choice-eval-20260523T093610Z.md` | API health unavailable |
| artifact redaction grep | no private payload leaks | no matches | 1 | Pass | command output | exit `1` means `rg` found no matches |

## 未运行项

| Item | Reason |
|---|---|
| `pnpm run eval:wagent:items` | optional regression not run in this closeout |
| `pnpm run eval:wagent:failure-recovery` | optional regression not run in this closeout |
| live Conversation eval | required 11.3.6.3 / 11.3.6.4 runs executed and failed |
| autonomous run | prohibited / out of scope |
| `verify-scenario` | out of scope |

## 后续事项

- Open a code-type fix iteration for the failed required gates.
- After the fix, rerun `pnpm run eval:wagent:pending-choice` and
  `pnpm run eval:wagent:planner-choice`.
- Do not mark 11.3.6 complete until both required evals return exit `0`.

## 2026-05-23 Service-available Rerun

| Command / Surface | Expected | Actual result | Exit code | Status | Evidence | Notes |
|---|---|---|---:|---|---|---|
| API health | API / DB available | HTTP 200, `database=ok` | 0 | Pass | `curl -i http://127.0.0.1:8001/health` | Run outside sandbox due local TCP restriction. |
| product `/items` | page available | HTTP 200 | 0 | Pass | `curl -i http://127.0.0.1:5176/items` | Run outside sandbox due local TCP restriction. |
| `pnpm run eval:wagent:pending-choice` | all required gates pass | `status=fail`; `case=pending_choice_multi_candidate status=fail`; required gates `13/14` | 1 | Fail | Sanitized program summary `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T095709Z.md`; session `71182c21-efdc-4aab-b0e4-3d432c28fc4e` | `public_choice_payload_sanitized` failed because public surfaces exposed `learned_path_id`. Raw rerun output is not submitted because the paired planner artifact failed redaction. |
| `pnpm run eval:wagent:planner-choice` | all required gates pass | `status=fail`; `planner_backed_choice status=fail`; `planner_single_path_bypass_regression status=pass` | 1 | Fail | Sanitized program summary `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T095709Z.md`; session `4db454fb-4983-48a2-9ac1-716b6cde15fa` | Planner choice was created and selected, but execution did not start; execution / verification / final response gates failed. Raw rerun output is not submitted because it contained a full private path id. |
| strict private-id grep | no full private path id in submitted artifacts | raw planner rerun output contained a full private path id | 0 | Fail | command output | The raw runner artifact/result from the service-available rerun must not be committed. |
| program closeout result | result file written | `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T095709Z.md` | N/A | Written | result file | Program remains blocked. |

No autonomous run, `verify-scenario`, Console UI smoke, or direct replay substitution was used.

## 2026-05-23 Final Closeout Rerun

| Command / Surface | Expected | Actual result | Exit code | Status | Evidence | Notes |
|---|---|---|---:|---|---|---|
| `git rev-parse --short HEAD` | final fix commit recorded | `f2d7d55` | 0 | Pass | command output | Eval rerun started from clean fix HEAD. |
| `pnpm run eval:wagent:items` | items and single-path direct replay pass | `status=pass`; `items_closed_loop status=pass`; `single_path_direct_replay_regression status=pass` | 0 | Pass | `artifacts/wagent-eval/wagent-runtime-eval-20260523T134338Z.json`; `docs/testing/results/m11-11.3.6.1-wagent-runtime-eval-core-20260523T134338Z.md`; session `88c1412d-d3e5-4039-adc6-fb8d515c794b` | Items required gates `10/10`; direct replay regression required gates `9/9`. |
| `pnpm run eval:wagent:failure-recovery` | failure recovery pass | `status=pass`; `failure_recovery_menu_safety status=pass` | 0 | Pass | `artifacts/wagent-eval/wagent-runtime-eval-20260523T134459Z.json`; `docs/testing/results/m11-11.3.6.2-failure-recovery-eval-20260523T134459Z.md`; session `b60d7b4c-3ea5-473d-a47b-5990943bdfe1` | Required gates `11/11`; failure trigger uses eval-only hook. |
| `pnpm run eval:wagent:pending-choice` | pending choice pass | `status=pass`; `pending_choice_multi_candidate status=pass` | 0 | Pass | `artifacts/wagent-eval/wagent-runtime-eval-20260523T134741Z.json`; `docs/testing/results/m11-11.3.6.3-pending-choice-multi-candidate-eval-20260523T134741Z.md`; session `0933b2ba-f300-4f63-9b8c-fd197f96b912` | Required gates `15/15`; eval-only candidate binding caveat applies. |
| `pnpm run eval:wagent:planner-choice` | planner and single-path bypass pass | `status=pass`; `planner_backed_choice status=pass`; `planner_single_path_bypass_regression status=pass` | 0 | Pass | `artifacts/wagent-eval/wagent-runtime-eval-20260523T135028Z.json`; `docs/testing/results/m11-11.3.6.4-planner-backed-choice-eval-20260523T135028Z.md`; session `8423e8c9-5b46-4958-a499-41086ad24ea2` | Planner required gates `17/17`; bypass required gates `8/8`; `planner_top_choice_observable` is non-required `not_observable`. |
| redaction grep | no private payload / selector / full path id leaks | no matches | 1 | Pass | command output | exit `1` means `rg` found no matches. |

Closeout decision: completed after fix rerun. The program can be marked closed / pass with
documented caveats; no autonomous run, `verify-scenario`, Console UI smoke, or direct
replay substitution was used.
