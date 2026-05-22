# 意图（Intent）

状态：draft_for_review（failure recovery eval 设计稿，未实现代码）

## 背景

11.3.5.8 已经实现基础失败恢复：当 replay failed、blocked、evidence missing、
needs review 或 uncertain 时，WAgent 应给出保守的 A/B/C recovery menu：

```text
A. 重试执行该操作
B. 重新学习
C. 取消
```

11.3.6.1 runner core 先覆盖 `/items` happy path 和 single-path direct replay regression。
下一步需要把 failure recovery 纳入同一套 eval program，让它不是只靠 targeted unit tests
和人工读事件，而是能通过 runner 产出可审计 artifact 和 hard gates。

## 目标

本迭代目标是为 WAgent Runtime Eval Runner 增加 failure recovery eval coverage：

- 可稳定触发一个 failure / needs-review recovery path。
- 验证 WAgent visible reply 出现正确 recovery menu。
- 验证 retry 文案明确为“重试执行该操作”，并在可能重复 side effect 的场景提示风险。
- 验证 relearn / cancel 出口存在。
- 验证 private retry payload 不进入 visible response、public session payload 或 public events。
- 验证 verified happy path 不出现 recovery menu。

## 非目标

- 不实现复杂自治恢复。
- 不实现自动 retry 成功闭环。
- 不把 recovery eval 扩展到登录、权限、验证码、cookie 或敏感输入场景。
- 不把 `verify-scenario` 或 autonomous-run endpoint 纳入本 runner 默认路径。
- 不改 product model、Agent role table 或 M12 recovery / abort 范围。

## 成功标准

实现完成后，应满足：

- `failure_recovery_menu_safety` case 可以由 runner 执行并写出 JSON / Markdown artifact。
- required gates 由结构化 evidence 判定，不由 Codex 主观判断。
- redaction gate 能覆盖 learned path id、slot overrides、selector、ReplayAction、private retry map
  等私有字段泄露风险。
- failure trigger 的来源明确且可复现；不可观察字段只能标记 `not_observable` / `warning`。
- non-live tests 和 safety checks 通过；未运行 live eval 时，review 不声称 live pass。
