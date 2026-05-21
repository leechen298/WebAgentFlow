# 11.3.5.x Working Runtime Iteration Plan

状态：planning  
父迭代：11.3.5 · Customer-Facing Agent Router & Skill Runtime  
关联施工稿：[`working-runtime-construction.md`](./working-runtime-construction.md)

## 1. 背景

11.3.5 working runtime 施工稿已经确认 P0 闭环的关键链路：

```text
item_name slot
-> fill_values
-> LearnedPath value_slot
-> ReplayRequest slot_overrides
-> run_replay effective_action
-> runtime stop 前采集 evidence
-> Reporter verified path
```

本计划不一次性生成 11.3.5.3 到 11.3.5.9 的完整迭代文档集，而是先落一个轻量拆包计划，
把每个子迭代的目标、范围、验收重点和依赖关系固定下来，再逐个生成完整文档并施工。

## 2. 总目标

11.3.5.3 - 11.3.5.6 属于 P0 working loop，目标是证明 WebAgentFlow 可以学习一个
操作，并用用户提供的新参数执行该操作。

11.3.5.7 - 11.3.5.9 属于 P1 / P2 runtime robustness，目标是处理混乱输入、
多候选、失败恢复和复杂路径规划。

第一条 P0 窄闭环：

```text
新增 product-test-site /items
-> 学习新增项目，名称叫测试项目A
-> LearnedPath 绑定 value_slot=item_name
-> 执行新增项目，名称叫测试项目B-${timestamp}
-> replay 实际填入 B，不复读 A
-> [data-testid='item-list'] 中出现 B
-> TaskResultReporter 输出 verified
-> docs/testing/results 留下结果和日志复核记录
```

## 3. 分包原则

- 每个包都必须可验收、可回滚、可解释。
- P0 先做窄闭环，不把多候选、状态账本、失败恢复和 Planner 接入提前塞进去。
- 单路径 happy path 不经过 TaskPathPlanner；TaskPathPlanner 只服务多候选、模糊目标、
  planning preview / confirmed execution path。
- Internal Runtime Adapters 不是 Application Skills，不得出现在 Router skill menu。
- `learn_then_execute` 继续保守阻断，除非后续新增显式用户确认链路。
- 每个代码型子迭代开始前，必须生成完整迭代文档集，并以 reviewed 文档为施工依据。

## 4. 迭代表

| 迭代 | 目标 | 做什么 | 不做什么 | 验收重点 |
|---|---|---|---|---|
| [11.3.5.3](../11.3.5.3-product-test-site-items-fixture/) | `/items` 测试页 | 在 `apps/product-test-site` 新增 `/items`；只做新增项目、列表展示、状态提示、稳定 `data-testid` | 不接 `wagent chat`；不做 replay；不做 evidence；不做搜索 / 编辑 / 删除 | 页面可打开；新增项目后列表出现目标文本 |
| [11.3.5.4](../11.3.5.4-parameterized-learning-replay-slots/) | 参数化 learning / replay | `item_name` slot；`_fill_values_from_intake()`；学习后 `value_slot` 绑定；`ReplayRequest.slot_overrides`；`effective_action`；step log 证明 replay 填入 B | 不接 Reporter；不做 DOM evidence；不做 `pending_choice`；不接 TaskPathPlanner | 学习 A 后执行 B，实际填入 B，不复读 A |
| [11.3.5.5](../11.3.5.5-execution-evidence-result-reporter-adapter/) | ExecutionEvidence + Reporter adapter | replay 结束后、runtime stop 前采集 DOM evidence；限定 `[data-testid='item-list']`；`ExecutionEvidenceTarget.text -> ExecutionEvidence.target`；打通 Reporter verified path | 不做新页面；不改 Planner；不做 failure recovery 菜单 | replay succeeded + evidence verified 时 Reporter 输出 `verified` |
| 11.3.5.6 | `/items` 闭环测试方案与结果记录 | 写测试方案；跑“学习 A / 执行 B”；保留 step log、effective value、evidence、Reporter outcome；Codex 复核结果和日志 | 不新增验证 Agent；不扩大到搜索 / 编辑 / 删除；不修大功能，失败只记录问题和最小修复建议 | 形成可审计闭环证据 |
| 11.3.5.7 | `pending_choice` + 最小 `active_task` | 多候选 A/B/C；choice_id 私有映射；pending 过期 / 清理；最小 active task；cancel 清理 | 不接 TaskPathPlanner 复杂路径；不做 failure recovery；不做 `learn_then_execute` | 用户模糊输入时不乱猜，能进入 choice mode |
| 11.3.5.8 | 基础失败恢复 | replay 失败、URL 不匹配、evidence 不足时给“重试 / 重新学习 / 取消” | 不做复杂自治恢复；不做 LLM 自主探索；不做多步修复计划 | 失败时有安全出口，不编造成果 |
| 11.3.5.9 | TaskPathPlanner 多候选 chat 接入 | 多 learned actions、模糊目标、planning preview / confirmed execution 接入 choice mode | 不影响单路径 P0 happy path；不把 Planner 接成所有执行的必经节点 | 多候选时通过 Planner + choice 安全选择 |

## 5. 依赖关系

| 迭代 | 依赖 | 原因 |
|---|---|---|
| [11.3.5.3](../11.3.5.3-product-test-site-items-fixture/) | 11.3.5 施工稿 | 先提供稳定页面基座 |
| [11.3.5.4](../11.3.5.4-parameterized-learning-replay-slots/) | [11.3.5.3](../11.3.5.3-product-test-site-items-fixture/) | 参数化 learning / replay 需要 `/items` 新增项目场景验证 |
| [11.3.5.5](../11.3.5.5-execution-evidence-result-reporter-adapter/) | [11.3.5.4](../11.3.5.4-parameterized-learning-replay-slots/) | Evidence 和 Reporter 必须基于真实执行 B 的 replay 结果 |
| 11.3.5.6 | 11.3.5.3 - 11.3.5.5 | 只有页面、参数化 replay、evidence / reporter 都具备后，才能做闭环证据记录 |
| 11.3.5.7 | 11.3.5.6 | choice / ledger 应建立在已跑通的 P0 闭环上 |
| 11.3.5.8 | 11.3.5.6，可在 11.3.5.7 后 | 失败恢复需要有清楚的成功 / 失败 evidence 语义 |
| 11.3.5.9 | 11.3.5.7 | Planner 多候选接入依赖 choice mode 和私有映射 |

如果 11.3.5.7 施工时膨胀，可以拆成：

```text
11.3.5.7 pending_choice
11.3.5.8 active_task + cancel cleanup
11.3.5.9 basic failure recovery
11.3.5.10 TaskPathPlanner multi-candidate chat integration
```

当前先不拆太碎，继续按 11.3.5.3 - 11.3.5.9 规划。

## 6. 不做事项

- 不在本计划中一次性生成 11.3.5.3 - 11.3.5.9 的完整七件套。
- 不改代码。
- 不运行 E2E、UI smoke、`verify-scenario` 或 autonomous-run。
- 不把 `pending_choice`、`active_task`、failure recovery 或 TaskPathPlanner 接入塞进 P0。
- 不把 Internal Runtime Adapters 暴露为 Router 可推荐 skill。
- 不把 `localhost:5176` 作为 contract；实现必须使用 runtime target URL。
- 不把 `success / partial_success` 写成 TaskResultReporter 原生 outcome。
- 不实现搜索 / 编辑 / 删除项目闭环；P0 只验证新增项目。

## 7. 后续生成完整文档集规则

后续每个代码型子迭代开始前，都必须按 `docs/iterations/README.md` 和
`docs/iterations/templates/` 生成完整文档集：

```text
README.md
intent.md
contract.md
technical-design.md
test-plan.md
plan.md
review.md
```

生成顺序建议：

1. 先生成 [11.3.5.3 `/items` 测试页完整文档集](../11.3.5.3-product-test-site-items-fixture/)。
2. 评审通过后再实现 11.3.5.3。
3. 11.3.5.3 收口后，按同样方式生成 [11.3.5.4](../11.3.5.4-parameterized-learning-replay-slots/) 文档集。
4. 依次推进到 11.3.5.6，完成 P0 working loop。
5. P0 evidence 通过后，再进入 11.3.5.7 - 11.3.5.9。

每个子迭代文档必须引用本计划和
[`working-runtime-construction.md`](./working-runtime-construction.md)，并明确：

- 该子迭代属于 P0 working loop 还是 P1 / P2 runtime robustness。
- 本包依赖哪些前序包。
- 本包不做哪些后续能力。
- 本包的验收证据放在哪里。
