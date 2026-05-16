# 测试计划（Test Plan）

状态：proposed

## 目标

验证 M11.3 的 `wagent chat` 小白用户闭环，同时证明非 chat mode 的
preview / confirmation 行为未被破坏。

## Unit / Service Tests

### Chat intent

- 输入 `学习一下这个登录页怎么登录，地址是 http://localhost:5175/login` 判定为
  `learn_page` 并提取 URL。
- 输入 `learn this page http://localhost:5175/login` 判定为 `learn_page`。
- 输入 `帮我登录` 判定为 `execute_task`。

### Learning result

- learning service 返回 `run_id` 和 `learned_path_id`。
- 当 run 成功但 LearnedPath 未沉淀时，chat runtime 不返回“学习完成”。
- `/login` learn 使用 `spec_id=login`、`scenario=valid_credentials` 和
  `admin / 123456`。

### Session metadata

- 写入 `learned_actions` 时保留 metadata 里的其他字段。
- 同 alias 后写覆盖前写。
- event payload 记录 old/new path id。

### Chat runtime

- `interactive_chat` learn_page 追加 agent messages，并返回学习完成文案。
- `interactive_chat` 执行“帮我登录”时只匹配当前 session learned actions。
- 命中后直接 replay，不进入 `awaiting_confirmation`。
- 未命中时返回“还没学过这个操作，需要先学习。”
- 非 `interactive_chat` session 继续走现有 planning preview / confirmation。

## CLI Tests

- `wagent chat` 是顶层命令。
- 启动时创建 `current_mode=interactive_chat` session。
- session metadata 包含 `client=wagent_chat` 和
  `runtime_policy=auto_execute_happy_path`。
- 默认 timeout 为 `180s`，`--timeout` 可覆盖。
- REPL 支持多轮输入并打印 `WAgent > ...`。
- `exit` / `quit` / `:q` 正常退出。
- `wagent conversation start/send` regression 继续通过。

## Manual Smoke

环境端口：

- API: `http://localhost:8001`
- Console: `http://localhost:5174`
- validation-site: `http://localhost:5175`

人工验收：

```text
$ wagent chat
WAgent > 你好，我可以学习页面操作，也可以执行已经学会的操作。
You > 学习一下这个登录页怎么登录，地址是 http://localhost:5175/login
WAgent > 开始学习页面操作。
WAgent > 学习完成：我学会了登录页的登录操作。之后你可以说“帮我登录”。
You > 帮我登录
WAgent > 执行中。
WAgent > 登录完成。
You > 帮我导出报表
WAgent > 还没学过这个操作，需要先学习。
```

必须检查：

- LearnedPath catalog 中存在新路径。
- transcript 中包含用户可见 agent messages。
- “帮我登录”未出现确认门槛。

## Live Run Boundary

本轮开发测试默认使用 unit / integration / CLI tests。人工 smoke 会真实触发
autonomous exploration / Playwright / replay，只有在用户明确要求并且本地服务可用时执行。
没有真实运行证据时，不得声称 manual smoke 已完成。
