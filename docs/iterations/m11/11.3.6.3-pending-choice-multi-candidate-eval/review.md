# 评审记录（Review）

状态：implementation_complete_verified（runner case implemented，live eval pass）

## Current Decision

- Reviewer: ChatGPT
- Decision: implementation_complete_verified
- Code: implemented
- Live eval: pass
- Notes:
  - non-planner pending choice scope is correct.
  - candidate setup practicality is clarified.
  - choice A path verification uses internal raw comparison plus public hash / alias redaction.
  - planner-backed choice remains 11.3.6.4.
  - Runner case and package script exist on current `v0.1`.
  - 2026-05-23 final rerun after 11.3.6.6 fixes returned exit `0`.
  - `pending_choice_multi_candidate` passed all required gates.
  - Eval uses `setup_type=eval_only_candidate_binding`; it does not prove `/records` has
    three real distinct product actions.

## Design Summary

本迭代计划在 11.3.6.1 runner core 之上增加 `pending_choice_multi_candidate` case，
验证 11.3.5.7 pending choice A/B/C public choices、private map safety 和用户选择后执行正确
action 的闭环。

## Review Checklist

- [x] candidate setup contract 稳定，且不受全局旧 LearnedPath 污染。
- [x] pending choice gates 有明确 source 和 pass / fail semantics。
- [x] public / private payload redaction 覆盖 pending choice 和 selection。
- [x] A selection gate 能证明执行的是 choice A 对应 learned action。
- [x] planner-backed choice 被排除到 11.3.6.4。
- [x] direct replay / autonomous-run 边界清楚。
- [x] live eval not-run 规则清楚。

## Design Review Notes

- 候选 setup 允许优先使用 live distinct paths；当 `/records` 当前页面无法稳定产生三个 distinct
  product actions 时，第一版可以使用 `setup_type=eval_only_candidate_binding` 或 fixture，但必须
  明确 `live_multi_action_capability=false`，不能冒充完整 live multi-action product capability。
- `execution_uses_choice_A_path` 允许 runner 在内部用 raw `learned_path_id` 做 expected / actual
  比较；JSON / Markdown / public gate evidence 只能输出 alias、redacted hash 和 match result。
- planner-backed choice 明确留给 11.3.6.4，本包出现 planner events 时应 fail `planner_not_invoked`。

## Not Run

- Unit tests were not run during this closeout sweep.
- `verify-scenario` was not run.
- autonomous run endpoints were not called.

## Next Step

Open a code-type fix iteration for the public pending-choice payload leak, then rerun
`pnpm run eval:wagent:pending-choice`. Do not mark this package complete until the required
gate passes.

## 2026-05-23 Closeout Sweep

| Command / Surface | Expected | Actual result | Exit code | Status | Evidence | Notes |
|---|---|---|---:|---|---|---|
| `pnpm run eval:wagent:pending-choice` | pending choice eval pass or blocked artifact | `status=blocked`; `case=pending_choice_multi_candidate status=blocked` | 2 | Blocked | `artifacts/wagent-eval/wagent-runtime-eval-20260523T093605Z.json`; `docs/testing/results/m11-11.3.6.3-pending-choice-multi-candidate-eval-20260523T093605Z.md` | API health unavailable: `[Errno 1] Operation not permitted` |
| artifact redaction grep | no private payload leaks | no matches | 1 | Pass | command output | exit `1` means `rg` found no matches |

Closeout decision: blocked. This records the blocked environment result only; it is not a
successful implementation closeout.

## 2026-05-23 Service-available Rerun

| Command / Surface | Expected | Actual result | Exit code | Status | Evidence | Notes |
|---|---|---|---:|---|---|---|
| `pnpm run eval:wagent:pending-choice` | all required gates pass | `status=fail`; `case=pending_choice_multi_candidate status=fail`; required gates `13/14` | 1 | Fail | Sanitized program summary `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T095709Z.md`; session `71182c21-efdc-4aab-b0e4-3d432c28fc4e` | `public_choice_payload_sanitized` failed because a private pending choice token `learned_path_id` was observed in public messages/session/events. Raw rerun output is not submitted because the paired planner artifact failed redaction. |

Closeout decision: implementation review failed. Services were available and the eval ran
through Conversation API, but one required gate failed. This is no longer an environment
blocked result.

## 2026-05-23 Final Fix Rerun

| Command / Surface | Expected | Actual result | Exit code | Status | Evidence | Notes |
|---|---|---|---:|---|---|---|
| `pnpm run eval:wagent:pending-choice` | all required gates pass | `status=pass`; `pending_choice_multi_candidate status=pass`; required gates `15/15` | 0 | Pass | `artifacts/wagent-eval/wagent-runtime-eval-20260523T134741Z.json`; `docs/testing/results/m11-11.3.6.3-pending-choice-multi-candidate-eval-20260523T134741Z.md`; session `0933b2ba-f300-4f63-9b8c-fd197f96b912` | `setup_type=eval_only_candidate_binding`; `live_multi_action_capability=false`; `current_eval_real_path_count=1`. |
| latest JSON | stable case-family latest JSON exists | `artifacts/wagent-eval/wagent-runtime-eval-pending-choice-latest.json` | N/A | Pass | file present | Added for evidence hygiene. |
| redaction grep | no private payload / selector / full path id leaks | no matches | 1 | Pass | closeout grep output | exit `1` means `rg` found no matches. |

Closeout decision: implementation complete / verified. This package is pass with the
documented caveat that the A/B/C choices are eval-only alias bindings over one real path,
not proof of three live distinct product actions on `/records`.
