# Test Plan

状态：draft_requirements

## 目标

本迭代的详细测试方案不在迭代目录内长期维护。完整测试域文档已移到：

- [`docs/testing/features/wagent-chat-progress-evaluation.md`](../../../../testing/features/wagent-chat-progress-evaluation.md)

迭代目录只保留本包的开发验收入口：实现完成后，应按长期测试文档运行一轮
`wagent chat` / `wagent conversation send` 面客回复与过程日志评测，并把结果写入
`docs/testing/results/`。

## 本迭代测试范围

本轮测试关注：

- 最终 `user_response` 是否合理。
- 同一轮 conversation events / progress timeline / metadata 是否能解释工作过程。
- URL 输入是否先查已学记录，再决定询问、学习或执行。
- 未学 URL 是否能自动进入学习，并在学习成功后报告学会了什么。
- 缺账号、密码、验证码或用户判断时，是否请求用户协助，而不是报告“应用无法学习”。
- 工作过程中的阶段性反馈是否能通过结构化日志最终校验。

## 非目标

- 当前文档阶段不新增 `apps/cli/tests/test_conversation.py`。
- 当前文档阶段不执行用例。
- 当前文档阶段不触发 `verify-scenario` 或 autonomous run。
- 最终 `wagent chat` 终端阶段性反馈由用户人工验收；本文件只定义验收入口。

## 执行结果

实现完成后，新增结果报告：

```text
docs/testing/results/YYYY-MM-DD-wagent-chat-progress-evaluation.md
```

报告必须先判最终回复，再判过程日志，最后给出 overall 结论。
