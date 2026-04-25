# Phase 10 · Path abstraction & experience accumulation

本 Phase 的权威范围与动机见
[`docs/roadmap.md` § "Next — Phase 10"](../../roadmap.md)；本文件是
**迭代索引**，每个具体迭代见同目录下的 `<NN>-<slug>/` 子目录。

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

## 迭代索引

- [01-learned-path-persistence](./01-learned-path-persistence/) ——
  LearnedPath 表、page signature 三件套、`pass_gate=pass` 自动写回、
  信用生命周期、history 详情页的 Confirm / Mark wrong 按钮。
  状态：**完成（2026-04-25）**。端到端证据见迭代 review.md：
  `pass_gate=pass` / 5/5 / `run_id=6c97c030-…` /
  `learned_path_id=31d3cf58-…`。

> 后续迭代在启动时在本文件追加一行，不预先创建空目录。不删已完成或
> 已放弃的迭代目录（见 `docs/iterations/README.md` §"三条实操约定"）。
