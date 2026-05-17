# 技术设计（Technical Design）

状态：proposed（docs generated, implementation not started）

## 设计目标

把 M11.3.4 的 intake 结果接到代码侧 conversation memory，让用户多轮自然表达可以续接。

目标流程：

```text
User input
-> CLI neutral progress
-> Conversation Intake Agent
-> Orchestrator merges pending_target / pending_intake / recent context
-> Code scope check and policy decision
-> learning / replay / clarification
```

## API / Runtime

### Session metadata

在 session metadata 中增加：

- `pending_target`
- `last_mentioned_url`
- `last_no_path_reason`
- `recent_context_summary`

敏感 slots 仍遵循 M11.3.4 redaction 规则。

### Intake context

调用 Conversation Intake Agent 时传入：

- current user message
- pending_intake summary
- pending_target summary
- current session learned_actions
- recent message summary
- last no-path reason

LLM 只理解语言；Orchestrator 仍做最终判断。

### Orchestrator behavior

- 裸 URL -> save pending_target -> ask operation.
- learn_operation with missing target -> inherit pending_target when safe.
- execute_operation no path -> save target/no-path context -> ask whether to learn.
- provide_missing_info -> only valid when pending_intake exists.
- new URL conflicts with pending_target -> ask confirmation instead of merging.

### CLI progress

`wagent chat` 的本地 progress 改为：

- 明确学习：`我会打开浏览器学习：...`
- 明确执行：`我会打开浏览器执行：...`
- 模糊 / 裸 URL / 单词命令：`正在理解你的需求，请稍等。`

## Console History

History detail 继续显示 M11.3.4 的 provenance / trace。

本轮补充：

- no-path 引导事件。
- pending_target saved / cleared events。
- 代码裁决和 Agent 理解之间的区别。

## 非 interactive_chat

非 `interactive_chat` session 不启用本流程，继续走 preview / confirmation / developer workflow。
