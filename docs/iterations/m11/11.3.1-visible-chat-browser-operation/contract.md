# 契约（Contract）

状态：implementation_complete（scoped tests passed, manual visible-browser smoke pending）

## 概念 / 边界契约

### Visible chat browser operation

`visible chat browser operation` 指 `wagent chat` 触发的学习或执行过程默认打开一个用户可见的
Playwright Chromium 窗口。用户可以看到页面加载、表单输入、按钮点击和页面跳转。

这个概念只作用于 `session.current_mode == "interactive_chat"` 的产品入口，不改变
developer workflow。

### Browser visibility policy

`browser_visibility` 是 `wagent chat` 会话级运行策略：

- `visible`：默认值，学习和执行都以可见浏览器运行。
- `headless`：用户显式选择后台运行，学习和执行不显示浏览器窗口。

`browser_visibility` 是会话策略，不是每条消息临时伪造的权限。Conversation runtime 必须优先读取
session metadata；dispatch metadata 只能作为审计辅助。

### Built-in browser

本轮“打开浏览器”指使用项目 Playwright 安装的 Chromium。它不是用户系统 Chrome，不复用用户
Chrome profile，不读取用户浏览器 cookie，也不操作用户已有浏览器标签页。

## 状态 / 结果契约

本轮不新增 conversation status，也不改变 replay status semantics。

`interactive_chat` 的状态路径保持：

- learning / execution 开始和完成由 conversation messages / events 记录；
- session status 仍回到既有 `task_intake`；
- 非 `interactive_chat` session 继续走现有 planning preview / confirmation / execution gate。

浏览器可见性不参与 pass / fail 判定。它只改变 Playwright runtime 的 `headless` 参数。

## Schema / API 契约

### CLI contract

`wagent chat` 默认可见运行：

```bash
wagent chat
```

用户可选择后台运行：

```bash
wagent chat --headless
```

保留既有参数：

```bash
wagent chat --api-base http://localhost:8001
wagent chat --timeout 180
```

`--timeout` 仍然表示 CLI 等待后端 HTTP dispatch 返回的最长时间，不表示浏览器单步操作超时。

### Session metadata contract

`wagent chat` 创建 session 时必须写入：

```json
{
  "current_mode": "interactive_chat",
  "metadata": {
    "client": "wagent_chat",
    "runtime_policy": "auto_execute_happy_path",
    "browser_visibility": "visible"
  }
}
```

当用户指定 `--headless` 时：

```json
{
  "metadata": {
    "browser_visibility": "headless"
  }
}
```

后续 dispatch metadata 可以包含相同值用于审计，但不能作为唯一权限来源。

### Runtime option contract

Learning service 和 replay hook 必须能接收 chat runtime 传入的 `headless` 选项。

默认兼容规则：

- 非 `interactive_chat` 调用方未传 `headless` 时，保持既有 headless 默认行为。
- `interactive_chat` session metadata 为 `visible` 时，学习和执行传入 `headless=False`。
- `interactive_chat` session metadata 为 `headless` 时，学习和执行传入 `headless=True`。

## Evidence / Observation 契约

本轮允许的 evidence 来源：

- CLI 原始输出；
- 单元 / 集成测试输出；
- 人工 smoke 中用户实际看到的浏览器窗口行为；
- 必要时的截图或屏幕录制；
- 若学习链路触发真实 autonomous learning，必须继续遵守 WebAgentFlow live run evidence 规则。

不得把静态代码审查写成 UI smoke。没有真实打开浏览器时，不得声称“用户可见操作已验证”。

## 产品模型 / 范围 / 路线图对齐（Product Model / Scope / Roadmap Alignment）

- Product model 对齐：仍然是 L3 用户通过 WebAgentFlow 操作网页；不新增 internal Agent role。
- Scope boundary 对齐：只改变产品入口的浏览器可见性，不让 LLM 进入 per-step browser control。
- Roadmap / milestone 对齐：作为 M11.3 ordinary-user closed loop 的收尾增强，编号为 11.3.1。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A，因为本轮不改变 product lifecycle、Agent role 或 milestone boundary。

## 兼容性契约

- `wagent conversation ...` 不新增 visible 默认行为。
- explicit `/replay` developer command 不因本轮变成可见浏览器。
- 既有 API request / response envelope 不改变。
- 既有 session 没有 `browser_visibility` 时，chat runtime 可按 `visible` 处理；非 chat runtime 保持原行为。
- 既有 unit tests 中的 mock replay / learning handler 必须能通过默认参数或 adapter 保持可用。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：不改变 response envelope；如需要 session metadata 字段，只作为 metadata 扩展。
- Database schema：不新增 migration。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变。

## 非目标

- 不实现用户系统 Chrome / profile 复用。
- 不做多浏览器选择 UI。
- 不做 streaming step progress。
- 不让用户在浏览器中接管操作。
- 不改变 confirmation gate。
- 不把具体页面写成功能范围边界。

## 未决问题

- 无。当前决策：`wagent chat` 默认 visible，`--headless` opt-out。
