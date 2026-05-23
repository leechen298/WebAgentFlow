# 复盘 / 评审（Review）

状态：implementation_complete_verified（fixes implemented，final eval rerun pass）

## Current Decision

- Reviewer：ChatGPT
- Decision：implementation_complete_verified
- Code：implemented
- Live eval：pass
- Notes：
  - 11.3.6.6 作为代码型 fix 设计稿通过。
  - 实现范围仍限定为 11.3.6.5 service-available rerun 的 required gate failures。
  - pending choice public payload leak、planner choice no-execution、dynamic private-id
    artifact redaction fixes have landed.
  - Final closeout rerun returned exit `0` for required 11.3.6 eval commands.

## Initial Evidence

- Closeout summary:
  `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T095709Z.md`
- 11.3.6.3 session: `71182c21-efdc-4aab-b0e4-3d432c28fc4e`
- 11.3.6.4 session: `4db454fb-4983-48a2-9ac1-716b6cde15fa`
- Pending choice failure:
  `public_choice_payload_sanitized` failed because public surfaces exposed `learned_path_id`.
- Planner choice failure:
  choice A dispatch succeeded, but `chat_execution_started` was missing and execution / verification gates failed.
- Artifact safety failure:
  raw planner rerun output contained full private path id and was not committed.

## Design Review Checklist

- [x] pending choice public/private payload contract is precise.
- [x] planner route choice selection execution path is scoped and does not break single-path bypass.
- [x] runner dynamic private-id redaction is required before artifact write.
- [x] tests include redaction, pending choice execution, planner execution, and single-path regression.
- [x] required eval commands and pass criteria are explicit.
- [x] no autonomous-run / `verify-scenario` / direct replay substitution is introduced.

## Design Review Notes

- 设计评审结论：通过，可以进入实现。
- 本包不新增 eval case、不扩大 runtime 产品能力、不关闭 11.3.6 program。
- 实现阶段只修 pending choice public payload leak、planner-backed choice selection no-execution、
  runner raw artifact / dynamic private id redaction。
- 11.3.6.6 通过后必须回到 11.3.6.5 重新执行 closeout sweep。

## 未运行项

| Item | Reason |
|---|---|
| pytest | design review only |
| ruff | no code changed |
| `pnpm run eval:wagent:pending-choice` | not implemented yet |
| `pnpm run eval:wagent:planner-choice` | not implemented yet |
| `verify-scenario` | out of scope |
| autonomous run | prohibited / out of scope |

## Next Step

11.3.6.5 closeout status can be updated because the required eval commands reran and passed.

## 2026-05-23 Implementation Closeout

| Area | Result | Evidence |
|---|---|---|
| Pending choice public payload leak | fixed | `pnpm run eval:wagent:pending-choice` exit `0`; `pending_choice_multi_candidate` required gates `15/15`; `public_choice_payload_sanitized` pass |
| Planner choice no-execution | fixed | `pnpm run eval:wagent:planner-choice` exit `0`; `planner_backed_choice` required gates `17/17`; `planner_choice_execution_started` pass |
| Single-path planner bypass | preserved | `planner_single_path_bypass_regression` required gates `8/8` |
| Runner artifact redaction | fixed | redaction grep found no `pending_choice_private_map`, full `learned_path_id`, `selector`, `xpath`, `ReplayAction`, or raw credential fields in final submitted artifacts |
| Intake spurious ask flag | fixed after final items rerun exposed it | `fix: normalize complete intake ask state` (`f2d7d55`); targeted intake regression passed |

Final eval evidence:

- `artifacts/wagent-eval/wagent-runtime-eval-20260523T134338Z.json`
- `artifacts/wagent-eval/wagent-runtime-eval-20260523T134459Z.json`
- `artifacts/wagent-eval/wagent-runtime-eval-20260523T134741Z.json`
- `artifacts/wagent-eval/wagent-runtime-eval-20260523T135028Z.json`
- `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T135028Z.md`

No autonomous run, `verify-scenario`, Console UI smoke, or direct replay substitution was used.
