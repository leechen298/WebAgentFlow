# 意图（Intent）

状态：implementation complete（implementation review passed, UI smoke pending）

## 目标

为已有 Conversation 持久化补齐产品化 Chat History 与调试入口：API 能列出和聚合历史会话，Console 能查看会话历史，CLI 能 list / history / resume。

## 动机

当前系统已经有底层 conversation store、基础 API 和 `wagent conversation` 开发者命令，但人工测试 `wagent chat` 时仍然缺少可观察性：

- 只能通过终端输出判断一次聊天发生了什么。
- 不知道 session id 时无法复查历史。
- 知道 session id 后也需要分别调用 messages / transcript / events 再手动拼上下文。
- Console 只有 autonomous history 和 LearnedPath catalog，没有 Conversation / Chat History 页面。
- Codex CLI 若要基于某次历史会话继续调试，需要用户先提供 session id，并且调试入口太碎。

M11.3.1 解决“用户看得见浏览器操作”。M11.3.2 解决“开发者和外部 AI 调试员看得见会话过程”。两者共同补齐 interactive chat 的可用性和可观察性。

## 边界 / 非目标

- 本轮不新增任务规划、执行、学习、replay、Reporter、recovery 或 abort 能力。
- 不改变 ConversationStatus、ConversationEventType 或 replay status semantics，除非实现阶段发现现有字段无法表达 history read model；若发生，必须先更新 `contract.md`。
- 不新增数据库表；优先从现有 conversation 表和 session metadata 生成 read model。
- 不做复杂搜索、全文检索、标签系统、长期归档或批量导出。
- 不做账号体系、多用户权限、云端用户数据、数据脱敏策略或闭源产品壳。
- 不做 LLM 总结历史、任务评分系统、失败归因系统或 M12 recovery。
- 不触发 `verify-scenario`、autonomous run 或 product-driven live browser execution。
- 不让 Codex CLI 冒充内部 Supervisor Agent、Task Path Planner 或 Task Result Reporter。

## 成功标准

- `GET /conversation/sessions` 可以按 mode / status / time 条件列出最近 sessions，并返回消息数、事件数、最后用户消息、最后 agent 消息、learned action 数量。
- `GET /conversation/sessions/{session_id}/history` 可以一次性返回 session、messages、events、learned_actions、learning_runs、replay_summaries 和 raw JSON。
- Console 新增 `/conversation/history` 和 `/conversation/history/:session_id`，列表和详情页可用于人工复查 chat history。
- 详情页至少包含 Transcript、Events、Learned Actions、Replay / Learning Evidence、Raw JSON 视图，并能复制 session id / raw JSON。
- `wagent conversation list --mode interactive_chat --limit 20 --pretty` 可查看最近 chat sessions。
- `wagent conversation history <session_id> --pretty` 可输出完整 history payload。
- `wagent chat` 创建新 session 后输出本次 session id。
- `wagent chat --resume <session_id>` 可以继续一个已有 `interactive_chat` session。
- `wagent conversation send <session_id> --content "..." --pretty` 继续保持可用，Codex CLI 可用它向已知 session 追加调试输入。
- 所有新增 read surfaces 都忠实展示已持久化数据，不发明 internal Agent verdict，不把 `unverified` 或缺失 evidence 写成 pass。
