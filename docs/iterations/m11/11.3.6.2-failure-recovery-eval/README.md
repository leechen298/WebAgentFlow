# 11.3.6.2 · Failure Recovery Eval

状态：ready_for_implementation（design review passed，未实现代码）
里程碑：M11
类型：code
父迭代：[`11.3.6-wagent-runtime-eval-program`](../11.3.6-wagent-runtime-eval-program/)
前置迭代：
[`11.3.6.1-wagent-runtime-eval-runner-core`](../11.3.6.1-wagent-runtime-eval-runner-core/)、
[`11.3.5.8-basic-failure-recovery`](../11.3.5.8-basic-failure-recovery/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

11.3.6.2 是 WAgent Runtime Eval Program 的第二个执行包。它在 11.3.6.1 runner
core 之上增加 failure recovery eval coverage，用 hard gates 验证 11.3.5.8 已实现的
基础失败恢复边界：

```text
失败 / 证据不足
-> WAgent 给出 A/B/C recovery menu
-> visible reply 不泄露 private retry payload
-> recovery events 不泄露 selector / learned_path_id / slot_overrides 等内部载荷
-> verified happy path 不出现 recovery menu
```

本包不新增复杂自治恢复能力，也不把 retry 成功率作为首版验收目标。

## 本包做什么

- 在 eval runner 中新增 `failure_recovery_menu_safety` case family。
- 定义稳定、可审计的 failure trigger / eval-only hook contract。
- 校验 recovery menu 文案、retry 风险提示、relearn / cancel 出口。
- 校验 visible response、public session payload 和 recovery event 的 private payload redaction。
- 校验 verified happy path 不误触发 recovery menu。
- 增加 runner unit / integration tests 和安全回归检查。

## 本包不做

- 不新增产品级 Failure Recovery 能力。
- 不执行 retry 侧 effect 作为必过 gate。
- 不把 direct replay API 结果冒充 WAgent conversation runtime 闭环。
- 不调用 autonomous-run endpoints。
- 不默认调用 `verify-scenario`。
- 不运行登录页或敏感输入场景。
- 不把 Codex 自然语言判断作为 pass / fail 标准。

## 迭代文档

- `intent.md` - 目标、动机、边界和成功标准。
- `contract.md` - case、gate、fault injection、redaction、artifact 和 exit code contract。
- `technical-design.md` - runner 扩展、evidence collector、gate evaluator 和可选 eval-only hook 设计。
- `test-plan.md` - unit / integration / case / artifact / safety 测试矩阵。
- `plan.md` - 实施步骤、文件范围、验证命令和 review 收口。
- `review.md` - 本迭代设计评审和实现结果记录。

## 当前状态

设计评审已通过，可以进入实现。实现前必须先确认 11.3.6.1 runner core 的当前状态，并复核
11.3.5.8 recovery runtime 的现有可观测事件 / public payload。
