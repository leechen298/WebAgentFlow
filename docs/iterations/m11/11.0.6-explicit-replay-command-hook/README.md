# 11.0.6 · Explicit Replay Command Hook

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/scope-boundaries.md`
4. `docs/iterations/m11/m11-plan.md`
5. `docs/iterations/m10/10.2-replay-execution-drift-detection/plan.md`
6. `docs/iterations/m10/10.2-replay-execution-drift-detection/review.md`
7. `docs/iterations/m11/11.0.5-orchestrator-dispatcher/review.md`
8. 本目录的 `intent.md`
9. 本目录的 `plan.md`

状态：**已完成**。`16 passed`（replay hook）+ `29 passed`（API dispatch）+ `67 passed`（CLI）+ 原有 `101 passed` 无回归；ruff clean。

## 当前关系

- 前置：M10 replay execution + drift detection、11.0.5 Orchestrator
  Dispatcher。
- 本包：把显式 `/replay <learned_path_id> <url>` 接到 M10 replay。
- 后续：11.0.7 Conversation tests and evidence。
- 本包只处理 explicit replay command，不做 path selection / task planning。

## 硬边界

- 不做 LearnedPath selection。
- 不做 task-to-path planning。
- 不做 slot binding。
- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不把 replay result 包装成 `pass_gate` / Supervisor verdict。
- 不创建 M11.1 详情目录。

## 目标

将 M11.0 runtime conversation 中的显式
`/replay <learned_path_id> <url>` command 接入 M10 replay execution + drift
detection。

## 非目标

- 不根据自然语言任务选择 LearnedPath。
- 不做自动 path selection、slot binding 或 task-to-path planning。
- 不实现 Agent routing、recovery / abort dialogue、teaching mode、risk gate、
  artifact lifecycle 或 multi-page workflow。
- 不新增 full external CLI / Skill / Tool。
- 不改变 M10 replay contract。

## 成功标准

- `/replay <learned_path_id> <url>` 通过 Orchestrator 触发 M10 replay。
- replay command 必须显式包含 `learned_path_id + url`。
- missing args / malformed replay command 不执行 replay。
- dispatch response 包含 replay result summary 或 replay result object。
- conversation events 记录 replay requested / running / completed / failed
  lifecycle。
- 不做 path selection，不调用 autonomous run，不依赖 LLM provider。
- 不把 replay result 包装成 `pass_gate` 或 Supervisor verdict。
