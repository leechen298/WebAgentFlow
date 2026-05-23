# 复盘 / 评审（Review）

状态：draft_for_review（planner-backed choice eval 设计稿，未实现代码）

## Current Decision

- Reviewer：pending
- Decision：pending
- Code：not_started
- Live eval：not_run
- Notes：
  - 11.3.6.4 文档已生成，等待 design review。
  - 本包只准备 Planner-backed choice eval 的实现 contract。
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

## 待 review 问题

- `planner_top_choice_observable` 是否应保持 conditional，还是要求 implementation 先补最小只读
  top choice hash 暴露。
- 第一版是否允许 `eval_only_planner_candidate_binding` 使用 alias binding 验证 planner branch，
  并以 `planner_distinct_path_capability=false` 明确不声明 full live multi-action capability。
- `planner_single_path_bypass_regression` 是否作为独立 case，还是作为 `planner_backed_choice`
  的 required regression section。
