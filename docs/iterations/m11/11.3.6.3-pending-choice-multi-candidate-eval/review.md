# 评审记录（Review）

状态：ready_for_implementation（design review passed，未实现代码）

## Current Decision

- Reviewer: ChatGPT
- Decision: pass
- Code: not_started
- Live eval: not_run
- Notes:
  - non-planner pending choice scope is correct.
  - candidate setup practicality is clarified.
  - choice A path verification uses internal raw comparison plus public hash / alias redaction.
  - planner-backed choice remains 11.3.6.4.

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

- 候选 setup 允许优先使用 live distinct paths；当 `/items` 当前页面无法稳定产生三个 distinct
  product actions 时，第一版可以使用 `setup_type=eval_only_candidate_binding` 或 fixture，但必须
  明确 `live_multi_action_capability=false`，不能冒充完整 live multi-action product capability。
- `execution_uses_choice_A_path` 允许 runner 在内部用 raw `learned_path_id` 做 expected / actual
  比较；JSON / Markdown / public gate evidence 只能输出 alias、redacted hash 和 match result。
- planner-backed choice 明确留给 11.3.6.4，本包出现 planner events 时应 fail `planner_not_invoked`。

## Not Run

- 未实现代码。
- 未运行 unit tests。
- 未运行 live Conversation eval。
- 未触发 autonomous run。

## Next Step

可以按 `plan.md` 实现 runner case、必要的 eval-only setup hook、tests 和文档更新。
