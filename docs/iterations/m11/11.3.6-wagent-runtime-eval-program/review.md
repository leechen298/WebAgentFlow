# 复盘 / 评审（Review）

状态：accepted_program_plan（program review passed，docs-only）

## Current Decision

- Reviewer：ChatGPT
- Decision：accepted_program_plan
- Code：not_started
- Live eval：not_run
- Notes：
  - 11.3.6 作为 WAgent Runtime Eval Program 总纲通过。
  - 11.3.6.1 承接第一版 runner core 实现。
  - 11.3.6.2+ 按 case family 后续独立开包。

## 2026-05-22 拆分规划

- Author：Codex
- Decision：docs_created
- Notes：
  - 用户判断 11.3.6 更适合作为总体测试规划，runner core 应下沉到 11.3.6.1。
  - 已将原 `11.3.6-wagent-runtime-eval-runner` 移动为
    `11.3.6.1-wagent-runtime-eval-runner-core`。
  - 新增 `11.3.6-wagent-runtime-eval-program` 作为 runtime eval 总纲。
  - 11.3.6.1 保留 ready-for-implementation 状态。
  - 后续 11.3.6.2 / 11.3.6.3 / 11.3.6.4 按 case family 独立开包。

## 设计评审收口

- Reviewer：ChatGPT
- Decision：pass
- Notes：
  - 11.3.6 program 方向通过，作为总纲文档可以保留。
  - 11.3.6.1 runner core 通过，可以进入实现。
  - 本包仍为 docs-only，不实现 runner，不运行 eval。

## 未运行项

| Item | Reason |
|---|---|
| pytest | docs-only split |
| ruff | no Python changed |
| eval runner | not implemented in this package |
| autonomous run | prohibited / out of scope |
| `verify-scenario` | out of scope |

## 后续事项

- 用户确认拆分后，可以从 11.3.6.1 开始实现 runner core。
- 11.3.6.2 failure recovery 的稳定 fault injection / eval-only hook 设计已通过评审。

## 2026-05-22 子包开包记录

- Author：Codex
- Decision：docs_created
- Notes：
  - 已创建 `11.3.6.2-failure-recovery-eval` 作为下一个 child package 文档包。
  - 11.3.6 program 仍保持 docs-only，不在 program 包内实现 runner 代码。
  - 11.3.6.2 当前状态为 `ready_for_implementation`，design review 已通过，可以进入实现。

## 2026-05-23 子包开包记录

- Author：Codex
- Decision：docs_created
- Notes：
  - 已创建 `11.3.6.3-pending-choice-multi-candidate-eval` 作为下一个 child package 文档包。
  - 11.3.6 program 仍保持 docs-only，不在 program 包内实现 runner 代码。
  - 11.3.6.3 当前状态为 `ready_for_implementation`，design review 已通过，可以进入实现。

## 2026-05-23 Planner 子包开包记录

- Author：Codex
- Decision：docs_created
- Notes：
  - 已创建 `11.3.6.4-planner-backed-choice-eval` 作为下一个 child package 文档包。
  - 11.3.6 program 仍保持 docs-only，不在 program 包内实现 runner 代码。
  - 11.3.6.4 当前状态为 `ready_for_implementation`，design review 已通过，可以进入实现。

## 2026-05-23 Planner 子包设计评审收口

- Reviewer：ChatGPT
- Decision：ready_for_implementation
- Notes：
  - `eval_only_planner_candidate_binding` 允许作为第一版 setup fallback，但必须显式记录 capability flags。
  - `planner_top_choice_observable` 保持 conditional，不可观察时只能 warning / not_observable。
  - `planner_single_path_bypass_regression` 作为 11.3.6.4 required regression 保留。
  - 11.3.6 program 仍保持 docs-only，不在 program 包内实现 runner 代码。

## 2026-05-23 Program closeout 子包开包记录

- Author：Codex
- Decision：blocked
- Notes：
  - 已创建 `11.3.6.5-runtime-eval-program-closeout` 作为 11.3.6 program 收口扫尾包。
  - 当前最新 `v0.1` runner 代码已覆盖 pending choice 和 planner-backed choice eval scripts。
  - 11.3.6.3 / 11.3.6.4 的 review 状态和 result artifacts 已按 2026-05-23 closeout sweep
    回填为 blocked。
  - 11.3.6.5 不新增 runner 功能；只定义如何运行 / 记录 eval、回填 review、同步 program 与 M11 索引。
  - blocked artifact 只能证明 blocked 被记录，不得让子包或 program 进入 completed /
    `closed_live` / `closed_non_live` 状态。

## 2026-05-23 Program closeout sweep

- Author：Codex
- Decision：blocked
- Commit：`51967a7`
- Evidence：
  - `pnpm run eval:wagent:pending-choice` -> exit `2`, `status=blocked`,
    `artifacts/wagent-eval/wagent-runtime-eval-20260523T093605Z.json`,
    `docs/testing/results/m11-11.3.6.3-pending-choice-multi-candidate-eval-20260523T093605Z.md`
  - `pnpm run eval:wagent:planner-choice` -> exit `2`, `status=blocked`,
    `artifacts/wagent-eval/wagent-runtime-eval-20260523T093610Z.json`,
    `docs/testing/results/m11-11.3.6.4-planner-backed-choice-eval-20260523T093610Z.md`
  - Program closeout result:
    `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T093610Z.md`
- Notes：
  - Both evals blocked during preflight because API health was unavailable.
  - No autonomous run, `verify-scenario`, Console UI smoke, or direct replay substitution was used.
  - M11.3.6 remains blocked, not complete.
