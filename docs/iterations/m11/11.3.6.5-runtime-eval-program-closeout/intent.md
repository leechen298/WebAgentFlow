# 意图（Intent）

状态：draft_for_review

## 目标

把 M11.3.6 WAgent Runtime Eval Program 从“runner 能力已陆续加入”收口为一份可审计的
program-level 状态：每个 11.3.6.x 子包都有明确 implementation / live / non-live / blocked
结论、对应 artifact，且 M11 索引不再和 runner 代码事实脱节。

## 动机

当前最新 `v0.1` 代码中，`scripts/evals/wagent_runtime_eval.py` 已经扩展到
`SCHEMA_VERSION = "11.3.6.4"`，并包含 failure recovery、pending choice、planner-backed
choice 等 case；`package.json` 也已有对应 eval scripts。

但迭代文档状态没有完全收口：

- 11.3.6.1 已有 live eval pass closeout。
- 11.3.6.2 已有 non-live implementation closeout。
- 11.3.6.3 review 仍写 `Code: not_started` / `Live eval: not_run`。
- 11.3.6.4 review 仍写 `Code：not_started` / `Live eval：not_run`。
- `docs/testing/results/` 目前只有 11.3.6.1 / 11.3.6.2 result。

继续开新功能前，需要先把已实现 eval program 的证据和状态对齐，避免后续 Agent 误判
M11.3.6 已完全完成或仍完全未实现。

## 边界 / 非目标

- 不写 runner 新功能，不新增 API、service、schema、CLI behavior。
- 不修 pending choice / planner choice runtime bug；发现 bug 时另开代码型 fix。
- 不运行 autonomous-run endpoints；不调用 `verify-scenario`，除非用户后续明确要求。
- 不使用 Codex 自然语言判断替代 runner hard gates。
- 不把 blocked path、fixture pass、unit pass 写成 live Conversation eval pass。

## 成功标准

- 11.3.6.3 和 11.3.6.4 的 review 文档反映真实实现状态，而不是继续停留在
  `ready_for_implementation`。
- 对 `pnpm run eval:wagent:pending-choice` 和 `pnpm run eval:wagent:planner-choice` 有明确
  pass / fail / blocked / not_run 记录和 artifact 路径。
- 11.3.6 program README / review、M11 README、`m11-plan.md` 与子包状态一致。
- 如果 live eval 未运行，文档明确写 `live Conversation eval: not_run`，并解释风险。
- 如果任何 closeout gate fail，M11.3.6 不标 complete，而是记录 blocked / follow-up。
