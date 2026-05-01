# Phase 10 · Path abstraction & experience accumulation

本 Phase 的权威范围与动机见
[`docs/roadmap.md` § "Next — Phase 10"](../../roadmap.md)；本文件是
**迭代索引**。Phase 10 使用语义编号目录，目录前缀与任务编号保持
一致，例如 `10.1.1-autonomous-use-case-catalog/`。阶段级拆分与
外包执行顺序见 [`phase-plan.md`](./phase-plan.md)。

## 本 Phase 的总目标（摘自 roadmap）

从"引擎能开一个页面"过渡到"引擎能复用学过的东西并覆盖更多控件形
态"。六个交付项（并非必须同一迭代完成）：

1. **LearnedPath 持久化** —— `pass_gate = pass` 的运行自动落成可复用记录。
2. **Popup-based control 支持** —— 两段式"点触发 → 弹层内操作"。
3. **Custom click-toggle 控件** —— Tag-as-filter 这类伪控件。
4. **Form-label extractor 扩展** —— +6 个 UI 库 handler。
5. **Cross-page pattern mining** —— 识别 login / search / CRUD 共性。
6. **Replay execution + drift detection** —— 依学过的 path 回放。

## Phase 10 同时显式化的产品约束

[`docs/product-model.md` §10.7 Instance-local data & the shell boundary](../../product-model.md)
在本 Phase 开局一并写入 —— 约束 LearnedPath 的 schema（不加多租户
列）和反馈回路（在 history 详情里做 Confirm / Mark wrong，不做任何
账号体系）。新增持久化类表**必须**遵守此节。

## Phase 10 主线清单

- **10.1 LearnedPath persistence** —— 已完成。`pass_gate = pass`
  的运行沉淀为 LearnedPath，并提供 trust 生命周期。
- **10.1.1 Autonomous use-case catalog** —— 可执行。当前插入的
  辅助入口需求，不改变 engine，只把 authored specs 展示成可进入
  workbench 的用例目录。
- **10.2 Replay execution + drift detection** —— draft。消费
  LearnedPath，做回放和漂移判断。
- **10.3 Popup-based control support** —— draft。支持 Cascader /
  DatePicker / 表头筛选等弹层控件。
- **10.4 Custom click-toggle controls** —— draft。支持 Tag / pill
  等非原生点击切换控件。
- **10.5 Form-label extractor coverage expansion** —— draft。扩展
  常见 UI 库的 label handler。
- **10.6 Cross-page pattern mining** —— draft。归纳 login / search /
  CRUD 等跨页面共性。

## 执行包索引

- [10.1-learned-path-persistence](./10.1-learned-path-persistence/) ——
  LearnedPath 表、page signature 三件套、`pass_gate=pass` 自动写回、
  信用生命周期、history 详情页的 Confirm / Mark wrong 按钮。
  状态：**完成（2026-04-25）**。端到端证据见迭代 review.md：
  `pass_gate=pass` / 5/5 / `run_id=6c97c030-…` /
  `learned_path_id=31d3cf58-…`。
- [10.1.1-autonomous-use-case-catalog](./10.1.1-autonomous-use-case-catalog/) ——
  在 workbench 之前补一个“当前可跑自主探索用例”的目录页，让外部执行者
  能从 authored specs 直接进入对应场景的 workbench。状态：
  **可执行**。
- [10.2-replay-execution-drift-detection](./10.2-replay-execution-drift-detection/) ——
  状态：**draft only，不可直接外包执行**。
- [10.3-popup-based-control-support](./10.3-popup-based-control-support/) ——
  状态：**draft only，不可直接外包执行**。
- [10.4-custom-click-toggle-controls](./10.4-custom-click-toggle-controls/) ——
  状态：**draft only，不可直接外包执行**。
- [10.5-form-label-extractor-expansion](./10.5-form-label-extractor-expansion/) ——
  状态：**draft only，不可直接外包执行**。
- [10.6-cross-page-pattern-mining](./10.6-cross-page-pattern-mining/) ——
  状态：**draft only，不可直接外包执行**。

> 后续新增执行包时，目录名必须和任务编号一致。不删已完成或已放弃的
> 迭代目录（见 `docs/iterations/README.md` §"三条实操约定"）。
