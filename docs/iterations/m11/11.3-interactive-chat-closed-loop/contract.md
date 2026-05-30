# 契约（Contract）

状态：accepted（manual smoke passed）

## 概念 / 边界契约

### Interactive Chat

`interactive_chat` 是 M11.3 新增的 runtime mode，表示用户通过产品化 REPL
入口 `wagent chat` 与 WebAgentFlow 对话。它不同于现有开发者命令
`wagent conversation send`。

`wagent chat` 创建 session 时必须设置：

```json
{
  "current_mode": "interactive_chat",
  "metadata": {
    "client": "wagent_chat",
    "runtime_policy": "auto_execute_happy_path"
  }
}
```

Conversation runtime 只有在 `session.current_mode == "interactive_chat"` 时启用
M11.3 chat happy path。`dispatch.metadata.client == "wagent_chat"` 只作为审计信息，
不得作为唯一权限判断。

### Learn Page Intent

学习意图使用 deterministic 规则：

- 文本包含 `学习` / `学一下` / `learn` / `teach` 之一；
- 文本包含 URL；
- 判定为 `learn_page`。

第一版只支持 `/entry` happy path。`https://example.invalid/entry` 映射到：

- `spec_id=login`
- `scenario=valid_credentials`
- `fill_values={"username": "admin", "password": "123456"}`

### Session Learned Action

学习成功后，当前 conversation session metadata 写入：

```json
{
  "learned_actions": [
    {
      "alias": "登录",
      "utterances": ["帮我登录", "登录一下"],
      "learned_path_id": "...",
      "target_url": "https://example.invalid/entry",
      "page_template": "/entry",
      "scenario": "valid_credentials"
    }
  ]
}
```

同一 session 内 `learned_actions` 按 `alias` 去重；同 alias 后写覆盖前写。
event payload 必须保留 old/new path id，便于 review。

M11.3 interactive chat 执行匹配只使用当前 session `learned_actions`。全局
LearnedPath retrieval fallback 明确推迟到后续迭代。

## 状态 / 结果契约

- `learn_page` 成功：返回“开始学习页面操作。”和“学习完成...”用户可见消息。
- `learn_page` 失败：不得返回“学习完成”；返回学习失败或内部错误。
- `execute_task` 命中当前 session learned action：直接 replay，不进入
  `awaiting_confirmation`。
- `execute_task` 未命中：返回“还没学过这个操作，需要先学习。”
- CLI 必须在等待后端同步处理前给普通用户可理解的即时反馈：
  - 学习登录页时：`我会学习：在登录页输入账号密码，并点击“登录”按钮。`
  - 执行登录时：`我会执行：输入账号密码，并点击“登录”按钮完成登录。`
  - 未学过任务也要先说明用户请求的操作，例如：`我会执行：导出报表。`
- 普通用户可见输出不得包含 selector、className、id、LearnedPath、run_id、
  replay id、confidence score 等开发者内部信息。

## Schema / API 契约

本轮不新增外部 HTTP endpoint。继续使用：

- `POST /conversation/sessions`
- `POST /conversation/sessions/{session_id}/dispatch`

内部需要新增或扩展 service contract：

- learning service 必须返回 `run_id` 和 `learned_path_id`。
- 实现不得只依赖当前 `/exploration/autonomous-runs` response，因为现有 endpoint
  只暴露 `run_id`，不直接暴露 `learned_path_id`。
- 更新 `session.metadata.learned_actions` 时必须先读取当前 metadata，在 service
  代码中完成 alias 去重覆盖，再 patch 更新后的完整数组。

CLI 契约：

- 新增顶层 `wagent chat`，必须在 `apps/cli/wagent/main.py` 注册。
- `wagent chat` 默认 HTTP timeout 不低于 `180s`，支持 `--timeout` 覆盖。
- `wagent conversation ...` 保持开发者 workflow，不改为人工验收主入口。

## Evidence / Observation 契约

- “学习完成”必须以 LearnedPath 真实沉淀为准：
  - learning service 返回 `learned_path_id != None`；
  - repo / catalog 可查询到该 path。
- chat happy path 必须把用户可见的 WAgent 回复追加为 agent message，包括：
  - `开始学习页面操作。`
  - `学习完成：我学会了登录页的登录操作。之后你可以说“帮我登录”。`
  - `执行中。`
  - `登录完成。`
  - `还没学过这个操作，需要先学习。`
- CLI 可以把后端返回的通用等待语去重，改为更面向普通用户的动作级反馈；
  transcript 仍保留后端 agent messages 作为审计记录。

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：M11.3 仍属于 L3 actual work 的 runtime loop foundation，
  不新增 internal Agent role。
- Scope boundary 对齐：不引入账号体系、外部产品壳、托管用户数据或闭源 shell。
- Roadmap / milestone 对齐：M11.3 是 M11 runtime loop 的产品化入口补齐。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

- 非 `interactive_chat` session 继续走现有 planning preview / confirmation /
  execution via replay 逻辑。
- 11.1.5 confirmation gate 不删除、不重写。
- `wagent conversation start/send/messages/transcript/events` 继续可用。
- 现有 `wagent verify` 不受影响。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：不新增外部 endpoint。
- Database schema：不新增 migration；复用 `conversation_sessions.metadata_json`。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变；M12 范围不进入本轮。

## 非目标

- 不做 global LearnedPath fallback。
- 不做多 Path 歧义处理。
- 不做 streaming conversation。
- 不做 `/records` 或真实业务页面。
- 不做自动猜测页面、追问、推荐页面或失败恢复。

## 未决问题

- 无。第一版按本 contract 执行。
