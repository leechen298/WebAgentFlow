# M10 · Path Asset Foundation

> Directory note: this folder is the delivery milestone directory
> `docs/iterations/m10/`. In roadmap language this is **delivery
> milestone M10**, not a product lifecycle stage. Product lifecycle
> stages are L1 / L2 / L3 in `docs/product-model.md`.

M10 的权威范围与动机见
[`docs/roadmap.md` § "M10 — Path Asset Foundation"](../../roadmap.md)；
本文件是**迭代索引**。M10 使用语义编号目录，目录前缀与任务编号保持
一致，例如 `10.1.1-autonomous-use-case-catalog/`。里程碑级拆分与执行
顺序见 [`m10-plan.md`](./m10-plan.md)。

## 开发前必读

开发任何 M10 执行包前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/iterations/m10/m10-plan.md`
4. 对应执行包目录下的 `intent.md`
5. 对应执行包目录下的 `plan.md`

`draft only` 执行包不能直接施工。每次只实现当前执行包，不顺手做
后续编号任务；需要 live autonomous run 时只能通过
`verify-scenario` skill，不能直接调用 `/exploration/autonomous-runs`
或 `/exploration/autonomous-runs/stream`。

## M10 的总目标（摘自 roadmap）

从"引擎已经学会一条路"过渡到"这条 LearnedPath 是可查看、可信任、
可重跑、可解释漂移的路径资产"。

1. **LearnedPath 持久化** —— `pass_gate = pass` 的运行自动落成可复用记录。
2. **LearnedPath catalog** —— 路径资产主入口、trust 操作、actions 查看。
3. **Replay execution + drift detection** —— 指定一条已学 path 回放，
   页面变化 / 目标缺失时返回可解释状态。

## M10 closure note

M10 已完成路径资产基础能力。LearnedPath 现在可以持久化、查看、执行
trust 操作、显式 replay，并在页面变化或目标缺失时返回可解释 drift。

M10 收口证据包括 10.1 LearnedPath persistence、10.1.5 catalog、10.2
replay execution + drift detection、deterministic E2E，以及 Codex
exploratory validation 的首轮证据型报告。下一步进入 **M11.0 Runtime
Conversation Shell & Agent Orchestration**，不是继续施工 10.3。

测试证据：

- [Replay 测试域](../../testing/features/replay.md)
- [10.2 Replay E2E 首次实跑结果](../../testing/results/2026-05-08-replay-e2e-first-run.md)
- [M10.2 Replay E2E Codex 探索式验证报告](../../testing/results/2026-05-08-replay-e2e-codex-exploratory.md)

原 `10.3`–`10.6` 的 popup / click-toggle / label / pattern 草案仍保留
在本目录中，但不再是 M10 关闭的主线前置条件；它们被重新归入 roadmap
的 **M14 Learning Quality Agents & Coverage Expansion** backlog，除非
用户显式要求重新评估。它们仍是 **draft only，不可直接施工；M14
backlog**。

## M10 同时显式化的产品约束

[`docs/product-model.md` §10.7 Instance-local data](../../product-model.md)
在 M10 开局一并写入 —— 约束 LearnedPath 的实例内数据边界、session
失效后的恢复 / 用户沟通路径，以及反馈回路（run review 在 history 中
完成，LearnedPath trust 在独立 catalog 中完成）。新增持久化类表
**必须**遵守此节。

## M10 主线清单

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
- **10.2 Replay execution + drift detection** —— 已完成。消费
  LearnedPath，指定一条已学路径做 replay，并返回页面变化 / 目标缺失
  等可解释状态。replay API、LearnedPath catalog replay UI、
  deterministic E2E、Codex exploratory validation 首轮证据报告均已交付。
  它不实现 Agent D，不实现 L3 task runner。
- **10.3 Popup-based control support** —— draft，已迁入 M14 backlog。
- **10.4 Custom click-toggle controls** —— draft，已迁入 M14 backlog。
- **10.5 Form-label extractor coverage expansion** —— draft，已迁入
  M14 backlog。
- **10.6 Cross-page pattern mining** —— draft，已迁入 M14 backlog。

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
  指定 LearnedPath replay、drift 状态、step log 和 catalog 薄入口。
  状态：**完成（2026-05-08）**。交付包括 replay API、catalog drawer
  replay 区块、deterministic E2E，以及 Codex exploratory validation
  首轮证据型报告。
- [10.3-popup-based-control-support](./10.3-popup-based-control-support/) ——
  状态：**draft only，不可直接施工；M14 backlog**。
- [10.4-custom-click-toggle-controls](./10.4-custom-click-toggle-controls/) ——
  状态：**draft only，不可直接施工；M14 backlog**。
- [10.5-form-label-extractor-expansion](./10.5-form-label-extractor-expansion/) ——
  状态：**draft only，不可直接施工；M14 backlog**。
- [10.6-cross-page-pattern-mining](./10.6-cross-page-pattern-mining/) ——
  状态：**draft only，不可直接施工；M14 backlog**。

> 后续新增执行包时，目录名必须和任务编号一致。不删已完成或已放弃的
> 迭代目录（见 `docs/iterations/README.md` §"三条实操约定"）。
