# 10.2 极简版

10.2 要做一件事：让一条已经学会的 LearnedPath 能被重新执行一次，并在
失败时说清楚是页面变了、目标找不到、动作不支持，还是运行出错。

## 本轮做什么

1. 从 LearnedPath catalog 选择一条路径。
2. 输入一个 URL。
3. 后端打开页面，重新计算 page signature。
4. 对比 stored signature 和 current signature。
5. 检查已存 action 的 selector 是否还存在。
6. 按原 action 顺序执行 `fill` / `click` / `press` / `observe`。
7. 返回 replay status、drift status、warnings、step logs、final URL /
   title。

## 本轮不做什么

- 不做自然语言任务入口。
- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
- 不做 Runtime Conversation Surface / CLI。
- 不做 task planner、slot binding、task result verification。
- 不做 teaching mode、risk gate、artifact lifecycle、multi-page workflow。
- 不调用 autonomous run 创建接口，不把 replay 说成 `pass_gate` 或
  Supervisor verdict。

## 开发顺序

1. `steps/01-replay-schema.md`
2. `steps/02-candidate-selection.md`
3. `steps/03-drift-checker.md`
4. `steps/04-shared-action-executor.md`
5. `steps/05-replay-api.md`
6. `steps/06-catalog-ui.md`
7. `steps/07-tests-and-review.md`
