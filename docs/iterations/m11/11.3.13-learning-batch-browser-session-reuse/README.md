# 11.3.13 Learning Batch Browser Session Reuse

状态：PACKAGE_COMPLETE
里程碑：M11
类型：mixed / code-gated package

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [x] 混合型迭代

混合型迭代按代码型迭代门禁处理。本包已通过 read-only design review，
scoped repo-local implementation 已完成。未运行也不声明 live validation、
`verify-scenario` 或 Console UI smoke。

## 为什么放在 11.3.13

本问题和 11.3.12.2 `LearningBatch` 生命周期关系最强，但 11.3.12 父包已经
`PACKAGE_COMPLETE`，`CURRENT_STATE.md` 也明确 `active_child_package: none`、
`do_not_reimplement: true`。重新追加 `11.3.12.5` 会破坏父包 closeout 语义。

因此本包作为 M11.3 post-closeout sibling package：`11.3.13`。

它不进入 M12 recovery / abort，也不进入 M14 learning quality。它只解决 L1 product
learning 在一个 batch 内反复启动/关闭 visible browser 的资源生命周期和用户体验问题。

## 目标

在一次 URL-only / product-level learning batch 内，只启动一个用户可见的项目内置
Playwright Chromium，所有 scenario 复用同一个 batch-scoped runtime；batch 完成、
取消、超时或失败后再统一关闭浏览器。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - batch browser session、scenario reset、cleanup、evidence 契约。
- `technical-design.md` - ExecutionRuntime / LearningRunService / tests 的实现设计。
- `test-plan.md` - 非 live 单元 / 集成 / CLI 行为测试计划。
- `plan.md` - 文档与后续实现步骤。
- `review.md` - 当前文档生成复核和实现授权状态。

## 当前状态

本包处于 `PACKAGE_COMPLETE`。已实现 capability discovery learning batch 内
batch-scoped `ExecutionRuntime` 复用、scenario reset gate、reset failure
fail-closed 行为、BrowserEventRecorder listener cleanup，以及 scoped regression
tests。当前 reset gate 包含 target-agnostic 控件状态、结果区计数、结果区内容/结构、
页面状态指纹，
network terminal evidence 要求同一 action scope 内 request / response 配对；
reset failure 会持久化 minimal unverified `ExplorationRun` 作为 batch history
证据，但不会 ingest LearnedPath / LearnedCapability。live validation 仍需未来明确授权后单独运行。
