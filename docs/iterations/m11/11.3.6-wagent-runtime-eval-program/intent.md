# 意图（Intent）

状态：accepted_program_plan（program review passed，docs-only）

## 目标

把 11.3.6 定义为 WAgent Runtime Eval Program 的总纲，而不是单个 runner 实现包。

成功状态：

```text
11.3.6 总体规划
  -> 定义 eval program 的评价原则和通用证据契约
  -> 规划 11.3.6.1 / 11.3.6.2 / 11.3.6.3 / 11.3.6.4
  -> 把已通过评审的 runner core 下沉到 11.3.6.1
  -> 后续每个 case family 单独实现、验证、收口
```

## 动机

最初的 11.3.6 文档同时承担了两层职责：

- runtime eval 的总体原则：hard gates、artifact、exit code、redaction、Codex 审计边界。
- runner v1 的具体实现方案、case gates、API driver、evidence collector 和 artifact writer。

这两层混在一个包里会让后续 failure recovery、pending choice、planner choice 扩展不够清楚。
把 11.3.6 调整为总体规划后，11.3.6.1/2/3/4 可以按 case family 分别推进，避免一个迭代
塞进过多 live runtime 行为。

## 本包不做

- 不实现 runner。
- 不新增测试代码。
- 不新增 npm script。
- 不写 generated artifact。
- 不跑 `verify-scenario`、autonomous run、Console UI smoke 或 live eval。
- 不改变 11.3.5 working runtime 功能。

## 成功标准

- M11 README 和 `m11-plan.md` 明确 11.3.6 是总体 eval program。
- 11.3.6 文档明确 11.3.6.1/2/3/4 子包边界。
- 11.3.6.1 文档承接第一版 runner 的具体实现文档，并保持 `ready_for_implementation`。
- ChatGPT review 的非阻断优化已落实：`review.md` 使用清晰的 final decision。
- 本轮保持 docs-only，不声称任何 runtime eval 已执行。
