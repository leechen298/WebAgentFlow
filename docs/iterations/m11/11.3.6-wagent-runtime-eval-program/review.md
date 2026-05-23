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
