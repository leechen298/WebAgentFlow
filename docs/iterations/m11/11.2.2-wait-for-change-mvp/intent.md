# 11.2.2 Intent

状态：文档生成完成，能力未实现

## 本轮意图

11.2.2 的意图是把 11.2.1 的 Observation Signal Contract 推进成
Wait-for-change MVP 的文档级设计。

11.2.1 定义“观察到了什么”。11.2.2 定义“等待过程如何结束”。

本轮只写文档，不实现等待能力。

## 要回答的问题

- replay 执行一个 action 后，系统应该等什么变化？
- 等待结果应该如何表达？
- 哪些变化属于 MVP？
- 哪些变化暂不进入 MVP？
- timeout / skipped / not_required 应该如何记录？
- wait result 和 observation signal 是什么关系？
- wait 层和 Task Result Reporter 的边界在哪里？

## 与 11.2.1 的关系

11.2.1 的
[`contract.md`](../11.2.1-observation-signal-contract/contract.md)
定义 Observation Signal。11.2.2 不改变 signal kind，不创建 schema 文件，
也不实现 signal 采集。

11.2.2 只定义后续 wait-for-change 可以如何消费这些 signal，并把等待过程整理成
Wait Result。

## 与 11.2.5 的关系

11.2.2 不做 Agent 式业务解释。wait 层只等待、观察、记录。

Agent 式解释留给后续 11.2.5 evidence-aware Task Result Reporter。Reporter 可以在
完整 replay 执行结束后消费 observation signals 和 wait results，并生成保守的
任务结果汇报。

## 与 M12 的关系

M12 处理 recovery、retry、abort、interruption 和 user takeover。11.2.2 不处理这些
决策。

Wait Result 可以记录 timeout，但 timeout 不自动等于 retry、abort、recovery 或
takeover。

## Page Understanding Agent 边界

11.2.2 不调用 Page Understanding Agent。

Page Understanding Agent 属于 L1 / M14 的页面学习语义理解角色；11.2.2 只处理
replay action 后短窗口 observation signals 和 wait results。

如果后续需要基于完整 replay evidence 做解释，应由 11.2.5 的 evidence-aware
Task Result Reporter 承接，而不是把 Page Understanding Agent 放进 wait loop。

## 明确不做

- 不写代码。
- 不新增测试代码。
- 不运行 E2E。
- 不修改 public API。
- 不修改 database schema。
- 不创建 Python / TypeScript schema 文件。
- 不修改 replay execution。
- 不修改 Task Result Reporter。
- 不实现 runtime observation。
- 不实现 wait-for-change。
- 不实现 page-load waiting。
- 不实现 mutation observer。
- 不实现 network observer。
- 不实现 WebSocket / SSE / polling observer。
- 不做 recovery / retry / abort / interruption / user takeover。
- 不使用 Agent 判断业务成功。
- 不实现 Page Understanding Agent。
- 不实现 Page Context Bridge。
- 不读取或保存 raw HTML。
- 不创建 M12 / M14 / 11.3 目录。
- 不执行 merge / tag / push。
