# 测试计划（Test Plan）

状态：proposed（docs generated, implementation not started）

## 单测

### 裸 URL

输入：

```text
http://localhost:5176/workspace-login
```

期望：

- 不调用 learning handler。
- 不调用 replay handler。
- 保存 `pending_target`。
- 回复询问用户想学习什么操作。

### 短句学习续接

已有 pending target 时输入：

```text
学习
```

期望：

- intent 可解析为 learn operation。
- 继承 pending target。
- 缺 slots 时追问。
- 不把“学习”作为 execute task。

### no-path 引导学习

输入：

```text
帮我登录 http://localhost:5176/workspace-login
```

当前 session 没有 learned action 时，期望：

- 保存 no-path context。
- 回复“这个页面我还没学过。要我先学习它吗？”
- 不跨站点匹配历史 path。

### CLI progress

覆盖：

- 裸 URL -> 中性 loading。
- 单独“学习” -> 中性 loading 或后端明确追问。
- 明确学习长句 -> 学习 progress。
- 明确执行已学动作 -> 执行 progress。

### 清理规则

覆盖：

- learning success clears pending_target。
- `/cancel` / `/abort` clears pending state。
- turns_remaining 用尽后清理。
- 新 URL 冲突时不自动合并。

### Regression

- M11.3.4 provenance / trace 不回退。
- 非 `interactive_chat` 继续走 preview / confirmation。
- sensitive redaction 仍生效。

## 人工 smoke

```text
You > http://localhost:5176/workspace-login
WAgent > 我看到了这个页面地址。你想让我学习这个页面上的什么操作？
You > 学习登录，账号 demo，密码 123456
WAgent > 我会打开浏览器学习：登录。
...
You > 帮我登录这个页面
WAgent > 我会打开浏览器执行：登录。
```

未运行真实 smoke 前，不得标记 accepted。
