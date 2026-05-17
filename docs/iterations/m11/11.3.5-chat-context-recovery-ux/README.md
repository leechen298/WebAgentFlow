# 11.3.5 · Chat Context Recovery UX

状态：proposed（docs generated, implementation not started）
里程碑：M11
类型：code

## 迭代定位

11.3.4 已完成 Conversation Intake Agent 基础设施：LLM / fallback 负责理解用户语言，
代码负责 schema 校验、scope、执行策略、response provenance 和 LLM trace。

人工 smoke 暴露出下一层产品体验问题：

```text
You > http://localhost:5176/workspace-login
WAgent > 我会打开浏览器执行：http://localhost:5176/workspace-login。
WAgent > 还没学过这个站点或页面，需要先学习。
You > 学习
WAgent > 我会打开浏览器执行：学习。
```

这不是 LLM 是否聪明的问题，而是代码侧 conversation memory 和 recovery UX 不完整：
裸 URL 没有保存成 pending target；短句“学习”不能引用上一轮 URL；no-path 只是冷拒绝；
CLI progress 会提前误导用户。

## 本轮目标

补齐 `wagent chat` 的小白用户上下文恢复体验：

- 裸 URL 不直接 execute。
- 裸 URL 保存为 pending target。
- 用户短句“学习”能引用上一轮 target。
- no-path 主动引导学习。
- 缺信息时追问。
- CLI loading / progress 不误导用户。
- History detail 能解释“Agent 理解 / 代码裁决 / 代码兜底 / 混合路径”。

## 边界

本轮不新增产品内部 Agent。继续使用 M11.3.4 的 Conversation Intake Agent。

核心原则：

```text
LLM 负责理解语言。
代码负责记住上下文、裁决 scope 和决定下一步。
Learning / Replay 负责真实浏览器动作。
```

## 文档

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`
