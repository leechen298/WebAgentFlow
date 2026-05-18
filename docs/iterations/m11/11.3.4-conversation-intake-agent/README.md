# 11.3.4 · Conversation Intake Agent

状态：implementation complete（scoped tests passed, real LLM smoke pending）
里程碑：M11
类型：code

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

混合型迭代按代码型迭代门禁处理。

## 迭代定位

11.3.4 补齐 `wagent chat` 的自然语言入口层。当前 11.3.3 已经把
product-test-site 和 validation-site 拆开，并通过 product-level CLI smoke；
但 `wagent chat` 仍主要依赖 deterministic parser、regex 和字符串匹配。

本包定义 **Conversation Intake Agent / 对话理解 Agent**：它负责把用户自然语言
转成结构化 intent、target、action、slots 和 missing fields。它不直接操作浏览器，
不调用 Playwright，不选择 LearnedPath，也不替代 Conversation Orchestrator。

核心原则：

```text
不是让 LLM 控制浏览器。
是让 LLM 理解用户说的话。
```

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - Intake Agent 角色、schema、pending intake、敏感信息和安全边界。
- `technical-design.md` - service 边界、session metadata、LLM/fake provider、chat runtime 集成。
- `test-plan.md` - 文档阶段检查、后续实现测试矩阵和负例验收。
- `plan.md` - 文档阶段和后续实现阶段拆解。
- `review.md` - 文档审核记录、用户反馈和后续 acceptance blockers。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 已记录文档阶段边界和 acceptance blockers。
- [x] 实现阶段已完成。
- [ ] LLM-backed intake smoke 已记录到 `review.md`。

## 当前状态

实现阶段已完成并提交：`a08d434 feat: add conversation intake provenance tracing`。
本轮完成 Conversation Intake Agent 基础设施、schema-constrained intake、
deterministic fallback、pending intake guardrails、sensitive redaction、
response provenance、redacted LLM trace 和 Conversation History detail 展示。

Scoped API / CLI / Console tests 已通过。真实 LLM-backed intake smoke 尚未执行，
因此不能把 LLM-backed acceptance 标记为通过。

当前人工测试暴露出的“小白用户裸 URL + 下一句学习”问题不作为 M11.3.4
阻塞项，已转入 11.3.5 Customer-Facing Agent Router & Capability Runtime。
