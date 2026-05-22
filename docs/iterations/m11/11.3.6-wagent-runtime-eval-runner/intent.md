# 意图（Intent）

状态：draft_for_review（文档已生成，未实现代码）

## 目标

新增一个正式的 WAgent Runtime Eval Runner，把 11.3.5 working runtime 的关键验收路径
从人工对话 / 人工摘证据升级为可重复执行的本地 eval：

```text
开发者 / Codex 执行 pnpm run eval:wagent:items
  |
  v
Runner 通过 Conversation API 创建 session、发送 turns、等待响应
  |
  v
Runner 读取 events / history / LearnedPath detail / raw responses
  |
  v
Runner 按 hard gates 判定每个 case
  |
  v
Runner 写 JSON raw artifact + Markdown result
  |
  v
required gates 全 pass 才 exit 0
```

第一版只覆盖最小但高价值的 working runtime 回归：

1. `items_closed_loop`
2. `single_path_direct_replay_regression`

## 动机

11.3.5.6 已经证明 `/items` P0 working loop 可以通过真实 runtime 完成，但它仍是一次
人工执行和人工整理结果。随着 11.3.5.7 pending choice、11.3.5.8 failure recovery、
11.3.5.9 planner choice 接入后，继续靠人工逐项聊天会有几个问题：

- Codex 容易变成“手动试一下再主观总结”，无法稳定复现。
- pass / fail 需要 hard gate，而不是自然语言判断。
- 每次运行都需要保留 raw record，方便用户和后续 Agent 审核。
- `/items` 闭环和单路径 direct replay 应该成为后续 runtime 改动的默认回归门槛。
- CLI `wagent conversation send` 已经具备 session-targeted dispatch 能力，但 eval 需要
  自己控制 timeout、artifact 和 gate，所以更适合直接调用 Conversation API。

本包的核心价值是让 Codex 成为审计员，而不是裁判：

```text
Eval Runner = 裁判：执行、采证、判 gate、写报告、给 exit code
Codex = 审计员：检查报告和 raw artifact 是否一致、是否越界、是否泄露 private payload
用户 = 最终验收人：接受或要求修正
```

## 为什么现在做

11.3.5 已经具备足够基础能力：

- Conversation API 可以创建 session、dispatch、读取 messages / events / history。
- `wagent conversation send` 已经证明 session-targeted dispatch 路径存在。
- `/items` product-test-site 已经作为稳定产品级测试页使用。
- 11.3.5.6 的 clean-slate pass chain 已经定义了可硬校验 gates。
- 11.3.5.9 引入 planner choice 后，必须保护“单路径明确目标直接 replay”不被回归。

继续向更复杂的 failure recovery、pending choice、planner choice 扩展前，先把两个最核心
case 自动化，能降低后续迭代的人工验证成本。

## 本包不做

- 不实现新的 Agent role。
- 不改变 Router / Orchestrator / Skill Runtime 产品契约。
- 不新增正式 M15 eval 平台、dashboard、历史趋势、trust trend 或 drift alert。
- 不在第一版覆盖登录页。
- 不在第一版覆盖 failure recovery fault injection。
- 不运行 `verify-scenario`。
- 不调用 `/exploration/autonomous-runs` 或 `/exploration/autonomous-runs/stream`。
- 不通过 direct replay endpoint 替代 Conversation API dispatch。
- 不把 Codex 的自然语言判断写成 gate pass。
- 不要求 runner 启动长期服务；runner 只做 preflight 和 blocked 报告。

## 成功标准

- `pnpm run eval:wagent:items` 能运行第一版用例。
- `items_closed_loop` 能创建 session、学习 A、执行 B，并按 hard gates 判定：
  - LearnedPath created。
  - LearnedPath fill action has `value_slot=item_name`。
  - execution has `slot_overrides.item_name=B`。
  - DOM evidence target selector is `[data-testid='item-list']`。
  - DOM evidence verifies B。
  - TaskResultReporter outcome is `verified`。
  - final WAgent response is evidence-based and mentions B。
- `single_path_direct_replay_regression` 能基于已学 path 执行 C，并证明单路径不进入
  pending choice / planner choice。
- runner 输出 JSON raw artifact 和 Markdown result。
- required gates 全 pass 时 exit `0`；required gate fail 时 exit `1`。
- API 或 product-test-site 不可用时 exit `2` 并写 blocked result。
- timeout 时 exit `3` 并保留已采集 raw record。
- artifact 写入失败和 runner 自身异常有独立 exit code。
- public reply / session public payload / events 不泄露 private payload。
