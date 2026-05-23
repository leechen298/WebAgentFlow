# 复盘 / 评审（Review）

状态：ready_for_implementation（design review passed，未实现代码）

## Current Decision

- Reviewer：ChatGPT
- Decision：ready_for_implementation
- Code：not_started
- Live eval：not_run
- Notes：
  - 11.3.6.4 方向通过，可以进入实现。
  - `eval_only_planner_candidate_binding` 允许作为第一版 setup fallback，但必须显式记录 capability flags。
  - `planner_top_choice_observable` 保持 conditional，不可观察时只能 warning / not_observable。
  - `planner_single_path_bypass_regression` 作为本包 required regression 保留。
  - 未修改 runner 代码，未运行 live Conversation eval。

## 设计关注点

- Planner-backed choice 必须通过 Conversation API 自然触发 runtime path。
- Runner 不得直接调用 `TaskPathPlanner.plan()`。
- Candidate setup 必须避免全局旧 LearnedPath 污染。
- 如果使用 eval-only planner candidate binding，artifact 必须明确 capability flags。
- Public artifact 不得泄露 `learned_path_id`、selector、slot overrides、private map、raw planner
  warnings 或 raw response text。
- 当前 public surface 可能无法观察 exact Planner top choice；相关 gate 必须 conditional，不得猜。

## 未运行项

| Item | Reason |
|---|---|
| pytest | docs-only draft |
| ruff | no Python changed |
| eval runner | not implemented in this package |
| live Conversation eval | not implemented / not requested |
| autonomous run | prohibited / out of scope |
| `verify-scenario` | out of scope |

## 设计评审收口

- `planner_top_choice_observable` 保持 conditional；如果 public read surface 不可观察，runner
  必须标记 `not_observable` / `warning`，不得猜测。
- 第一版允许 `eval_only_planner_candidate_binding` 使用 alias binding 验证 planner branch，但
  artifact / Markdown 必须记录 `live_multi_action_capability=false` 和
  `planner_distinct_path_capability=false`。
- `planner_single_path_bypass_regression` 是本包 required regression。实现上可以是独立 case，也可以
  是 `planner_backed_choice` 的 required section，但 artifact 必须单独列出 gates。
