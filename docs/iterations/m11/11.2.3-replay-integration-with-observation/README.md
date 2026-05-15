# 11.2.3 · Replay Integration with Observation

状态：implementation complete

## 目标

11.2.3 定义并准备实现 replay-level observation evidence aggregation。
它回答：replay 执行结束后，WebAgentFlow 应该如何把每个 step 的
`wait_result` 和 observation signals 聚合为可审计的 replay-level evidence。

实现阶段应按 `contract.md`、`technical-design.md` 和 `test-plan.md` 落地
schema、replay aggregation service、replay integration 和对应测试。11.2.3 仍不接入
Task Result Reporter。

## 背景

11.2.2 已完成最小 Wait-for-change MVP 代码能力：

- `ReplayStepLog.wait_result: WaitResult | None = None`。
- `apps/api/app/services/learning/wait_for_change.py`。
- 每个 replay step 可以携带 step-level wait outcome。
- 当前实际 primary / target signals 只有 `url_changed` 和 `title_changed`。
- `network_idle_observed` 只能作为 supporting signal。
- `page_load_finished` 保留在 schema 中，当前 MVP 不实际生成。

11.2.3 不重复实现 11.2.2。它定义下一层 replay integration 边界：如何把
step-level wait evidence 汇总到 replay result 的 observation evidence 层。

## 核心契约

核心契约见 [`contract.md`](./contract.md)。

`contract.md` 定义：

- Replay Observation Evidence。
- Replay Observation Summary 字段 proposal。
- replay observation status。
- 与 11.2.2 WaitResult 的关系。
- 与 11.2.5 Task Result Reporter 的关系。
- 与 later 11.2.x Common Component Runtime Semantics 的边界。
- 与 M12 recovery / retry / abort 的边界。

## 开发文档

- [technical-design.md](./technical-design.md)：代码实现的详细技术设计。
- [test-plan.md](./test-plan.md)：代码实现完成后的测试计划。
- [plan.md](./plan.md)：代码实现计划；更细执行依据以 `technical-design.md` 和
  `test-plan.md` 为准。

## 与 11.2.2 的区别

```text
11.2.2:
每个 replay step 后等一小段时间，并记录 step-level wait_result。

11.2.3:
把每个 step 的 wait_result / observation signals 汇总到 replay-level
observation evidence 层，形成后续 reporter 可消费的结构化输入。
```

11.2.3 不新增 wait strategy，不改变 11.2.2 当前支持的 signal 范围。

## 与 11.2.5 的关系

11.2.3 不接 Task Result Reporter。

11.2.3 只为 11.2.5 准备输入：

```text
11.2.3 produces replay-level observation evidence.
11.2.5 lets Task Result Reporter consume it.
```

Reporter 未来可以基于完整 replay evidence 做保守解释，但不能仅凭 observation
summary 推断任务一定成功、业务一定完成、timeout 后应该 retry 或 abort。

## 实现边界

- 可以按 `technical-design.md` 修改 replay response schema，新增可选
  `ReplayResult.observation_summary`。
- 可以按 `technical-design.md` 新增 replay observation aggregation service。
- 可以按 `technical-design.md` 在 replay result 返回前聚合 step-level
  `wait_result`。
- 可以按 `test-plan.md` 新增或更新 scoped unit tests。
- 不运行 E2E / live UI smoke / `verify-scenario` / autonomous run。
- 不新增 API route。
- 不修改 database schema。
- 不修改 Task Result Reporter。
- 不修改 conversation / task_planning / routers / CLI。
- 不实现 reporter integration。
- 不实现 recovery / retry / abort / user takeover。
- 不实现 Page Understanding Agent。
- 不实现 Page Context Bridge。
- 不实现 Common Component Runtime Semantics。
- 不读取 raw HTML。
- 不保存 raw HTML。
- 不创建 M12 / M14 / 11.3 目录。
- 不修改 package 文件。
