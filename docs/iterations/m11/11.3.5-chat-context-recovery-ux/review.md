# 复盘 / 评审（Review）

状态：proposed（docs generated, implementation not started）

## 2026-05-17 需求来源

- Reviewer：User / ChatGPT / Codex
- Decision：approved_for_docs_generation
- Trigger session：`a497358b-7c85-4b38-bf5a-7a8b555283fe`

## 发现的问题

人工输入：

```text
You > http://localhost:5176/workspace-login
WAgent > 我会打开浏览器执行：http://localhost:5176/workspace-login。
WAgent > 还没学过这个站点或页面，需要先学习。
You > 学习
WAgent > 我会打开浏览器执行：学习。
```

用户意图是：

```text
先提供目标页面
再要求系统学习这个页面
```

当前系统表现说明：

- 裸 URL 没有进入 pending target。
- 短句“学习”没有引用上一轮 URL。
- no-path 没有主动引导学习。
- CLI progress 在后端裁决前误导性地显示“执行”。

## 收口决定

M11.3.4 收口 Conversation Intake Agent 基础设施和 provenance / trace。
本问题作为 M11.3.5 Chat Context Recovery UX 独立处理。

## Acceptance Blockers

- 如果裸 URL 仍被直接当 execute，不得 accepted。
- 如果“学习”不能引用 pending target，不得 accepted。
- 如果 no-path 只冷拒绝不引导学习，不得 accepted。
- 如果 CLI 对模糊输入仍提前显示“执行”，不得 accepted。
- 如果实现让 LLM 直接操作浏览器，不得 accepted。
- 如果非 `interactive_chat` developer workflow 被改变，不得 accepted。

## 未完成 / 风险

- 当前只是文档阶段。
- 代码实现尚未开始。
- 真实小白用户 smoke 尚未执行。
