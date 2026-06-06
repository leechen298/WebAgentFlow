# 11.3.12 Bounded Learning and Composable Capability Assets

状态：PACKAGE_COMPLETE
里程碑：M11
类型：umbrella / campaign

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [ ] 混合型迭代
- [x] umbrella / campaign

本包是父级设计和 `/goal` 路由包，不直接授权运行时代码开发。运行时代码、schema、
API、service、测试或 migration 必须在 child package 中独立通过代码型门禁。

## 目标

为 L1 autonomous learning 增加比 LearnedPath 更低一层的可持久化原子能力资产，
并把筛选页、列表页、tab、弹窗、下载等场景的学习策略从“穷举完整路径组合”调整为
“有限学习原子能力，运行时可组合执行，成功后再沉淀 LearnedPath”。

## 背景

11.3.10 已经让 `/users` 这类筛选页不再只沉淀单个搜索按钮路径；11.3.11 已经补充
terminal / ingest evidence gate。但 clean-slate live validation 暴露了三个更底层的问题：

- `wagent chat` 超时后，后端 learning batch 仍继续跑，浏览器继续弹出。
- Pairwise / all-supported 组合数量容易膨胀，用户也不需要系统把所有组合都学完。
- 当前只有 ExplorationRun 和 LearnedPath，缺少“我会操作这个控件 / 按钮 / tab / 导出”的
  原子能力留存，导致 L3 只能选完整路径，不能安全组合已学能力。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - LearnedCapability、bounded learning、composition、batch lifecycle 契约。
- `technical-design.md` - schema / model / service / orchestration / compatibility 设计。
- `test-plan.md` - unit / integration / conversation / live-boundary 测试计划。
- `plan.md` - 文档与后续实现步骤。
- `review.md` - 当前文档生成复核和实现授权状态。
- `GOAL_RUNNER.md` - `/goal` campaign 路由契约。
- `CURRENT_STATE.md` - 当前 child package 路由快照。

## /plan 风格文档生成入口

- [x] 目标 package path 和 package type 已确定。
- [x] parent / child 关系：本包是 umbrella；实现拆到 11.3.12.x child packages。
- [x] 必需文件集合：七件套。
- [x] source-of-truth 输入已阅读：`docs/product-model.md`、`docs/iterations/README.md`、
  `docs/iterations/AGENTS.md`、M11 README、11.3.10 / 11.3.11 相关契约和 live validation。
- [x] contract / concept / status / evidence 变化已识别。
- [x] design-review gate 和 `test-plan.md` 触发状态已识别。
- [x] implementation authorization boundary 已写明。
- [x] umbrella / campaign package 判断：需要 `GOAL_RUNNER.md` / `CURRENT_STATE.md`。
- [x] stop conditions 和 handoff / checkpoint 已写明。

## 父包门禁

- [x] 父包 `intent.md` 已存在。
- [x] 父包 `contract.md` 已存在。
- [x] 父包 `technical-design.md` 已存在，作为 high-level design，不直接授权实现。
- [x] 父包 `test-plan.md` 已存在，作为 campaign-level 测试矩阵，不替代 child test-plan。
- [x] 父包 `plan.md` 已拆出 child package queue。
- [x] 父包 `GOAL_RUNNER.md` 已存在。
- [x] 父包 `CURRENT_STATE.md` 已存在。
- [x] `review.md` 已记录整包不授权实现和 child routing。

## Child Packages

- [11.3.12.1-learned-capability-asset-foundation](../11.3.12.1-learned-capability-asset-foundation/) -
  LearnedCapability asset foundation：schema / model / repo / migration / compatibility
  foundation。状态：PACKAGE_COMPLETE（repo-local tests passed；online DB migration unverified due local env）。
- [11.3.12.2-bounded-learning-batch-lifecycle](../11.3.12.2-bounded-learning-batch-lifecycle/) -
  Bounded Learning Batch Lifecycle：定义 durable learning batch、bounded policy、cancel /
  timeout / detach 语义。状态：PACKAGE_COMPLETE（140 focused tests passed；82 compatibility tests passed；
  offline Alembic SQL generation passed；online DB migration unverified due local env）。
- [11.3.12.3-page-understanding-capability-hints](../11.3.12.3-page-understanding-capability-hints/) -
  Page Understanding Capability Hints：定义 capability hint schema、region/control/terminal/dependency
  hints 和 bounded learning 消费边界。状态：PACKAGE_COMPLETE（58 focused tests passed；scoped ruff passed；
  hardcoding scan reviewed；live validation not run）。
- [11.3.12.4-capability-composition-runtime](../11.3.12.4-capability-composition-runtime/) -
  Capability Composition Runtime：定义 deterministic capability composition plan、candidate compatibility、
  LearnedPath preference、private execution handoff 和 promotion guard。状态：PACKAGE_COMPLETE（227 scoped
  tests passed；scoped ruff passed；hardcoding scan reviewed；live validation not run）。

## 当前状态

父包设计审查发现整包范围过大，不能直接实现。`11.3.12.1-learned-capability-asset-foundation`
和 `11.3.12.2-bounded-learning-batch-lifecycle` 已完成 repo-local implementation。`11.3.12.3`
也已完成 repo-local implementation。`11.3.12.4-capability-composition-runtime` 已完成 repo-local
implementation，因此父 campaign 进入 `PACKAGE_COMPLETE`。本 campaign 未运行 live validation、未调用
`verify-scenario`，也未新增 Console UI、public API 或 LLM browser-step execution。
