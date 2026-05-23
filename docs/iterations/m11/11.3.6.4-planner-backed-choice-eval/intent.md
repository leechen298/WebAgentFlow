# 意图（Intent）

状态：ready_for_implementation（design review passed，未实现代码）

## 背景

11.3.5.9 已把 TaskPathPlanner 接入 `wagent chat` 的多候选 / 模糊目标路径：当当前
session 有多个候选 learned actions，且用户目标无法被确定为单一路径时，Runtime 会把候选
交给 TaskPathPlanner，生成 planner-backed A/B/C choice，并在用户选择后执行对应 learned
action。

11.3.6.3 已规划 non-planner pending choice eval。它验证 public A/B/C choice、private map
safety 和选择后执行正确 path，但明确不覆盖 TaskPathPlanner-backed path。

11.3.6.4 的目标是把 11.3.5.9 的 planner-backed choice 从 targeted tests 推进到 WAgent
Runtime Eval Runner 的 hard-gate case family。

## 目标

新增一个 runner case：

```text
planner_backed_choice
```

它必须验证：

- 多候选 / vague goal 进入 planner-backed choice path。
- Runtime 记录 sanitized planner events。
- public choice payload 不泄露 private planner data。
- 用户选择后执行预期 learned action。
- verified happy path 输出 evidence-based success。
- 单路径明确目标仍绕过 Planner，直接 replay。

## 用户价值

开发者可以运行：

```bash
pnpm run eval:wagent:planner-choice
```

获得可审计 artifact：

```text
status=pass/fail/blocked/timeout
required gates
planner events
public/private payload safety evidence
single-path bypass Planner regression
```

这样 11.3.5.9 的 Planner 接入不会只停留在 unit / mocked targeted tests，而能纳入同一套
WAgent Runtime Eval Program。

## 成功标准

- Runner 支持 `planner_backed_choice` case。
- Case 通过 Conversation API 驱动 runtime conversation。
- Runner 不直接调用 `TaskPathPlanner.plan()`、direct replay API 或 autonomous-run endpoints。
- JSON artifact 和 Markdown result 明确记录 candidate setup type、live capability boundary、
  planner events、gate result 和 not-run items。
- Public artifact 不泄露完整 `learned_path_id`、selector、slot overrides、private map、raw
  planner warnings 或 execution payload。
- 如果当前 public read surface 无法观察 Planner top-choice 映射，runner 必须把对应 gate 标为
  `not_observable` / `warning`，不能猜。

## 非目标

- 不新增 TaskPathPlanner 排名能力。
- 不新增 Planner LLM 调用。
- 不改变 Router / Orchestrator / Skill Runtime 边界。
- 不把 all execute-operation 都强行走 Planner。
- 不把 non-planner pending choice 和 planner-backed pending choice 混成一个 case。
- 不运行 login page。
- 不声称未执行的 live Conversation eval pass。
