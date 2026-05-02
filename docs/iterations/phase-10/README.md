# Phase 10 · Path abstraction & experience accumulation

本 Phase 的权威范围与动机见
[`docs/roadmap.md` § "Next — Phase 10"](../../roadmap.md)；本文件是
**迭代索引**。Phase 10 使用语义编号目录，目录前缀与任务编号保持
一致，例如 `10.1.1-autonomous-use-case-catalog/`。阶段级拆分与
执行顺序见 [`phase-plan.md`](./phase-plan.md)。

## 开发前必读

开发任何 Phase 10 执行包前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/iterations/phase-10/phase-plan.md`
4. 对应执行包目录下的 `intent.md`
5. 对应执行包目录下的 `plan.md`

`draft only` 执行包不能直接施工。每次只实现当前执行包，不顺手做
后续编号任务；需要 live autonomous run 时只能通过
`verify-scenario` skill，不能直接调用 `/exploration/autonomous-runs`
或 `/exploration/autonomous-runs/stream`。

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
列）和反馈回路（run review 在 history 中完成，LearnedPath trust
在独立 catalog 中完成，不做任何账号体系）。新增持久化类表**必须**
遵守此节。

## Phase 10 主线清单

- **10.1 LearnedPath persistence** —— 已完成。`pass_gate = pass`
  的运行沉淀为 LearnedPath，并提供 trust 生命周期。
- **10.1.1 Autonomous use-case catalog** —— 已完成。在 workbench
  之前补一个“当前可跑自主探索用例”的目录页。
- **10.1.2 Scenario-relative verdict cleanup** —— 已完成。把
  pass_gate 的机械 verdict 映射到 scenario-relative 公开词汇。
- **10.1.3 Run review vs LearnedPath trust** —— 已完成。把 run
  级人工审核和 LearnedPath trust 拆成两个独立概念。
- **10.1.4 RESTful route cleanup** —— 已完成。把 run 端点统一到
  `/exploration/autonomous-runs` 等 RESTful 路径。
- **10.1.5 LearnedPath catalog** —— 已完成。给 LearnedPath 增加
  独立列表页和路径级 trust 操作入口。
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
  信用生命周期。初版 trust 操作曾在 history detail，当前有效入口已
  在 `10.1.5` 迁移到 LearnedPath catalog；history detail 只保留
  run review 和 LearnedPath 只读关联信息。
  状态：**完成（2026-04-25）**。端到端证据见迭代 review.md：
  `pass_gate=pass` / 5/5 / `run_id=6c97c030-…` /
  `learned_path_id=31d3cf58-…`。
- [10.1.1-autonomous-use-case-catalog](./10.1.1-autonomous-use-case-catalog/) ——
  在 workbench 之前补一个“当前可跑自主探索用例”的目录页。状态：
  **完成**。
- [10.1.2-scenario-relative-verdict-cleanup](./10.1.2-scenario-relative-verdict-cleanup/) ——
  机械 verdict → scenario-relative 公开词汇。状态：**完成**。
- [10.1.3-run-review-vs-learned-path-trust](./10.1.3-run-review-vs-learned-path-trust/) ——
  拆分 run 级人工审核与 LearnedPath trust。状态：**完成**。
- [10.1.4-restful-route-cleanup](./10.1.4-restful-route-cleanup/) ——
  统一 exploration router 到 RESTful 路径。状态：**完成**。
- [10.1.5-learned-path-catalog](./10.1.5-learned-path-catalog/) ——
  LearnedPath 独立列表页、trust 过滤、actions 查看和路径级操作入口。
  状态：**完成**。
- [10.2-replay-execution-drift-detection](./10.2-replay-execution-drift-detection/) ——
  状态：**draft only，不可直接施工**。
- [10.3-popup-based-control-support](./10.3-popup-based-control-support/) ——
  状态：**draft only，不可直接施工**。
- [10.4-custom-click-toggle-controls](./10.4-custom-click-toggle-controls/) ——
  状态：**draft only，不可直接施工**。
- [10.5-form-label-extractor-expansion](./10.5-form-label-extractor-expansion/) ——
  状态：**draft only，不可直接施工**。
- [10.6-cross-page-pattern-mining](./10.6-cross-page-pattern-mining/) ——
  状态：**draft only，不可直接施工**。

> 后续新增执行包时，目录名必须和任务编号一致。不删已完成或已放弃的
> 迭代目录（见 `docs/iterations/README.md` §"三条实操约定"）。
