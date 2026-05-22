# 意图（Intent）

状态：draft_docs（待评审，未开始实现）

## 目标

为 `wagent chat` 增加基础失败恢复能力。失败时，系统必须保守说明当前能确认什么、
不能确认什么，并给用户三个明确选择：

```text
A. 重试执行该操作
B. 重新学习
C. 取消
```

## 动机

11.3.5.6 已证明成功链路可以完成：

```text
学习 A
-> 执行 B
-> evidence verified
-> Reporter verified
```

但真实网页执行不会永远成功。按钮可能找不到、页面可能不匹配、replay 可能异常、
证据可能不足。当前 runtime 已经能保守报告一部分失败或不确定状态，但用户下一步
仍然需要自己重新组织语言。

本包的目标是让失败也有 code-owned 闭环：

```text
失败 / 不确定
-> 保守报告
-> 写 pending recovery choice
-> 用户选重试 / 重新学习 / 取消
-> Runtime 执行对应安全分支
```

## 边界 / 非目标

- 不让 LLM 自主探索页面修复。
- 不自动改 selector。
- 不做无限 retry。
- 不把 recovery 交给 TaskPathPlanner。
- 不做复杂多步骤恢复计划。
- 不新增 Failure Recovery Agent 的完整自治实现。
- 不启用 `learn_then_execute`。
- 不把重新学习后自动执行作为默认行为。
- 不运行 autonomous exploration。

## 成功标准

- replay failed 时，用户收到失败说明和 A/B/C 恢复选项。
- evidence missing / `needs_review` / `uncertain` 时，系统不说成功，而是提示无法确认并给恢复选项。
- URL mismatch / drift / blocked 时，系统不继续乱执行，并给恢复选项。
- 用户输入 `A` / `1` / `第一个` 后，Runtime 再次执行同一个 learned action，
  保留原 `slot_overrides`，并在文案中提示可能重复副作用。
- 用户输入 `B` / `2` / `第二个` 后，Runtime 进入重新学习分支，必要信息不足时追问。
- 用户输入 `C` / `3` / `第三个` 或“算了”后，清理 pending state 和 active task。
- retry / relearn / cancel 的 private payload 不暴露 `learned_path_id` 给用户、Router prompt 或 LLM trace。
- 既有 `/items` verified happy path 不受影响。
