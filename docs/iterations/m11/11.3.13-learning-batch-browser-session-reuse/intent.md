# Intent

状态：proposed

## 目标

解决 product-level URL-only learning / capability discovery 中 visible browser 反复弹出的问题。

当前用户体验是：一次学习批次里，seed analysis 会打开一次浏览器，每个 scenario 又会打开并关闭
一次浏览器。用户看到浏览器窗口反复弹出、关闭、再弹出。目标状态是：

```text
learning batch started
  -> open one visible Chromium
  -> seed analyze page
  -> run N scenarios in the same batch runtime
  -> close Chromium once when batch reaches terminal status
learning batch closed
```

## 动机

11.3.12 已经补了 `LearningBatch`、bounded learning 和 capability composition，但
`LearningRunService._run_capability_discovery()` 仍在每个 scenario 中用
`with runtime_factory(...) as runtime`。在 `wagent chat` 默认 visible browser 的产品入口下，
这会造成用户电脑上浏览器反复弹出。

这不是学习覆盖率问题，也不是 `/users` 特化问题；它是 learning batch 内 browser resource
lifecycle 的产品体验和资源治理问题。

## 成功标准

- 一次 capability discovery learning batch 默认只创建一个 `ExecutionRuntime`。
- seed analysis 和 scenario loop 复用同一个 browser/context/page，或者在同一 browser 下进行
  明确的 context/page reset 策略；不能每个 scenario launch 一个新 browser。
- 每个 scenario 开始前必须有可审计 reset / baseline gate。
- batch 完成、取消、超时、scenario exception、persist exception 时都必须关闭 runtime。
- BrowserEventRecorder、screenshots、terminal / ingest evidence 仍按 scenario 隔离。
- Existing spec-backed autonomous run、single product-level learning、replay 执行不被破坏。
- 文档明确不运行 live autonomous validation。

## 非目标

- 不实现跨 batch / 跨 conversation 的长期浏览器复用。
- 不复用用户真实 Chrome；仍使用项目内置 Playwright Chromium。
- 不实现 active browser tab support。
- 不实现 M12 recovery / abort 对话。
- 不实现 L2 teaching 或用户接管。
- 不改变 capability discovery 的覆盖策略。
- 不为 `/users` 或任何 validation site 写特化逻辑。

## 关键假设

- `run_autonomous_exploration()` 本身已经接受 caller-managed runtime，它不负责创建/关闭浏览器。
- 主要改动点在 `LearningRunService._run_capability_discovery()` 的 runtime ownership。
- 同一个 context/page 复用更符合用户看到的“一个浏览器窗口”，但需要 scenario reset gate 防止状态污染。
