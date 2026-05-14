# 11.2.0 · 运行时观察范围与真实场景目录

## 目标

初始化 M11.2 文档包和 realistic web runtime case catalog，让后续 11.2.x
可以围绕 runtime observation 展开，而不是滑进 recovery 或 retry 行为。

## 动机

M11.1 已完成第一个可工作的 task-to-path MVP：用户任务输入可以基于已有
LearnedPath 做规划、预览、确认、通过 replay 执行，并用保守证据汇报结果。

真实页面在 replay 动作后并不会静止。它们会出现 loading、toast、modal、
delayed button、partial refresh、SPA update，以及服务端驱动的被动变化。
如果没有一个明确命名的 observation scope，后续工作很容易把 wait-for-change、
result evidence、recovery、retry 和 abort 混成一团。

M11.2 先定义 observation layer。

## 当前范围

11.2.0 文档化：

- 为什么 M11.2 在 M11.1 之后存在。
- M11.2 和 M12 的边界。
- Post-action Observation。
- Passive Runtime Observation。
- realistic web runtime cases。
- 后续 11.2.x 拆包。

## 边界

本轮不做：

- 不写 runtime code。
- 不新增 test code。
- 不运行 E2E。
- 不修改 replay execution。
- 不修改 Task Result Reporter。
- 不实现 observation signal schema。
- 不实现 wait-for-change。
- 不创建 fixture。
- 不实现 recovery、retry、abort 或 user interruption。
- 不实现 teaching mode。
- 不触发 autonomous run。
- 不引入 LLM provider 依赖。
- 不读取 raw HTML。
- 不创建 M12 / 12.x 目录。
- 不创建 v0.2 分支。

## 成功标准

- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/` 存在，
  且包含 `README.md`、`intent.md`、`plan.md`、`review.md`。
- `docs/testing/scenarios/realistic-web-runtime-cases.md` 存在，并明确标注为
  scenario catalog，不是自动化覆盖记录。
- 文档区分 Post-action Observation 和 Passive Runtime Observation。
- 文档说明 M11.2 负责观察和记录 evidence，M12 负责 recovery / retry /
  abort / interruption。
- 文档说明 11.2.0 只是文档初始化。
- `git diff --check` clean。
- 不创建或修改代码、测试、package、v0.2、M12 或 12.x 文件。
