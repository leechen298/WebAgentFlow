# 契约（Contract）

状态：proposed（docs generated, implementation not started）

## 新增状态概念

### pending_target

`pending_target` 是代码侧 session memory，不是 LLM 自己记忆。

示例：

```json
{
  "pending_target": {
    "url": "http://localhost:5176/workspace-login",
    "site_origin": "http://localhost:5176",
    "page_hint": "工作台登录页",
    "source": "user_url_message",
    "turns_remaining": 3
  }
}
```

### last_no_path_reason

当用户请求执行但当前 session 没有匹配 learned action 时，代码记录 no-path 上下文，
用于下一轮把“那就学习”理解为学习上一个目标。

## 行为契约

### 裸 URL

如果用户只输入 URL：

```text
http://localhost:5176/workspace-login
```

系统不得直接 execute。应保存 `pending_target` 并回复：

```text
我看到了这个页面地址。你想让我学习这个页面上的什么操作？
```

### 短句学习

如果 session 存在 `pending_target`，用户输入：

```text
学习
```

系统应把它理解为学习 pending target，而不是执行“学习”这个任务。

如果还缺 action goal 或 slots，系统应追问，不得触发 browser action。

### no-path 引导

如果用户请求执行未学过的页面：

```text
帮我登录 http://localhost:5176/workspace-login
```

系统应保存 target，并回复：

```text
这个页面我还没学过。要我先学习它吗？
```

### CLI progress

CLI 不得在后端判断前把模糊输入渲染成“我会打开浏览器执行：学习”。

允许的中性提示：

```text
WAgent > 正在理解你的需求，请稍等。
```

学习或执行已经明确时，才显示具体 progress。

## 责任边界

- Conversation Intake Agent 可以识别 intent / target / action / slots。
- Conversation Orchestrator 必须保存、合并和清理 `pending_target` / `pending_intake`。
- Orchestrator 负责最终 user_response，不直接信任 LLM 文案。
- Learning / Replay 仍是唯一能触发真实浏览器动作的服务。
- Intake / pending target 只能作为 conversation evidence，不得写入 LearnedPath proof。

## 清理规则

`pending_target` 在以下情况清除：

- learning 成功。
- 用户 `/cancel`、`/abort`、`exit`。
- 用户明确提供新的 URL 并确认覆盖。
- `turns_remaining` 用尽。
- session 关闭。

target URL 变化时不得自动合并，必须追问确认。
