# wagent chat 入门指南

这份文档面向第一次使用 WebAgentFlow 的普通用户。它只说明怎么打开
`wagent chat`、怎么输入一句话、怎么看系统回复。

## 你能用它做什么

`wagent chat` 是一个命令行聊天入口。你可以用自然语言告诉 WebAgentFlow：

- 学习某个网页怎么操作。
- 执行已经学会的网页操作。

当前版本已经支持产品级工作台登录页 smoke，但自然语言理解仍在从规则匹配升级中。
如果一句话里没有提供页面地址或必要输入，系统可能无法像真正的对话 Agent 一样继续追问和续接。

M11.3.4 已新增 Conversation Intake Agent / 对话理解 Agent：它会把普通用户的话理解成
结构化的操作意图、目标页面、输入槽位和缺失信息。这个能力不是让 LLM 控制浏览器，
而是让 LLM 理解用户说的话；真正学习和执行仍由 WebAgentFlow 的 Learning / Replay 服务完成。
真实 LLM-backed smoke 尚未作为验收证据记录，所以如果你在本地没有配置 LLM provider，
系统仍可能走 deterministic fallback。

M11.3.4 同时增强聊天历史调试页：在
`http://localhost:5174/conversation/history/<session_id>` 中显示每条 WAgent 回复是代码生成，
还是由某个 WebAgentFlow 内部 Agent / LLM 生成，并提供脱敏后的 LLM provider / model /
raw trace。Codex CLI 只是外部测试或调试操作者，不会被当成 WebAgentFlow 内部回复者。

已知限制：当前入门 smoke 仍建议一次说清楚页面地址和必要输入。裸 URL 后再说
“学习”、未学过页面时主动引导学习、以及“我该先检查页面、学习还是执行”的面客
Agent 路由体验，已进入 M11.3.5 规划。

M11.3.5 计划新增 Customer-Facing Agent Router & Skill Runtime / 面客 Agent 路由与应用技能运行时。
它不是让 LLM 直接操作浏览器，而是让 Router 基于聊天上下文、页面理解、已学操作和
应用技能菜单建议下一步；代码侧 Orchestrator 再判断能不能执行，并通过注册 skill
调用 Learning / Replay 服务。M11.3.5 实现前，不要把“只发 URL 后系统能自动续接学习”
作为当前版本通过条件。

当前入门指南只验产品级工作台登录页：

```text
http://localhost:5176/workspace-login
```

`/users` 属于后续扩展测试，不作为这份入门指南的通过条件。

## 测试站点边界

`http://localhost:5175` 是 validation-site。它是工程验证靶场，用来做 deterministic
regression、spec / assertions、pass_gate、scorecard 和 `verify-scenario` 等基础能力验证。

`http://localhost:5176` 是 product-test-site。它和 validation-site 分开，用于产品级
`wagent chat` 人工验收：普通用户通过聊天提供页面地址和必要输入，系统再学习并执行网页操作。

项目的一键启动 `pnpm run dev` 应同时启动 product-test-site。

产品级聊天路径只学习用户输入的页面地址，只执行当前聊天里已经学过的站点或页面。如果你要求它操作
一个还没学过的站点，它应该清楚告诉你需要先学习，而不是拿别的测试站点路径去执行。

## 启动前准备

如果这是第一次启动本项目，先按仓库 README 或
[开发环境文档](../dev-setup.md) 完成安装。最少需要完成：

```bash
cd /Users/leechen/projects/WebAgentFlow/v0.1
pnpm install
python3.11 -m venv .venv
.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]' -e './apps/cli'
.venv/bin/python -m playwright install chromium
docker compose -f infra/docker/docker-compose.yml up -d
pnpm run db:migrate:api
```

只执行 `source .venv/bin/activate` 不会安装 `wagent`。`wagent` 是 CLI 包安装后生成在
`.venv/bin/wagent` 里的命令。

先在一个终端启动 WebAgentFlow：

```bash
cd /Users/leechen/projects/WebAgentFlow/v0.1
pnpm run dev
```

看到类似下面的地址后，就可以开始测试：

```text
console: http://localhost:5174
validation-site: http://127.0.0.1:5175
product-test-site: http://127.0.0.1:5176
api: http://0.0.0.0:8001
```

如果 `pnpm run dev` 没有正常启动，先不要继续测试，先解决启动问题。

## 进入聊天

另开一个终端：

```bash
cd /Users/leechen/projects/WebAgentFlow/v0.1

# 如果 wagent 还没有安装到虚拟环境，先安装 CLI
test -x .venv/bin/wagent || .venv/bin/pip install -e './apps/cli'

# 使用项目内 CLI 启动，不依赖当前 shell 是否已经激活 venv
.venv/bin/wagent chat
```

你应该看到：

```text
WAgent > 你好，我可以学习页面操作，也可以执行已经学会的操作。
You >
```

也可以使用激活虚拟环境的写法：

```bash
source .venv/bin/activate
wagent chat
```

但入门测试优先使用 `.venv/bin/wagent chat`，这样可以避免 shell `PATH` 没指向当前项目
虚拟环境的问题。

## 入口排障

如果看到：

```text
zsh: command not found: wagent
```

说明当前 shell 找不到 `wagent` 命令。不要只重复 `source .venv/bin/activate`，先执行：

```bash
cd /Users/leechen/projects/WebAgentFlow/v0.1
test -x .venv/bin/wagent || .venv/bin/pip install -e './apps/cli'
.venv/bin/wagent chat
```

如果 `.venv/bin/wagent` 存在，但 `wagent chat` 这个子命令不存在，通常说明当前虚拟环境里安装的是旧版
CLI。重新安装 CLI 后再检查：

```bash
.venv/bin/pip install -e './apps/cli'
.venv/bin/wagent --help
```

`--help` 里应该能看到 `chat` 命令。

当前版本默认会打开项目内置 Playwright Chromium，你可以看到页面加载、输入、点击和跳转。

如果你不想看到浏览器窗口，可以使用后台运行：

```bash
.venv/bin/wagent chat --headless
```

## 入门测试样例

在 `wagent chat` 中输入：

```text
学习一下这个工作台登录页怎么进入，地址是 http://localhost:5176/workspace-login，操作员账号是 demo，访问口令是 123456
```

当前版本建议尽量一次说清楚页面地址和必要输入。M11.3.5 会继续处理裸 URL、
短句学习意图、no-path 学习引导，以及先说明目标、后补充必要输入这类多轮说法。

M11.3.5 也会把底层能力整理成应用能力菜单，包括检查目标页面、基于 HTML AST /
Simplified AST / PageAnalysis 理解页面、查询当前会话已学操作、启动学习、执行已学路径、
以及在 MVP 支持范围内、信息完整时先学再执行。第一版仍以聊天里提供的 URL 和上下文为主，不依赖
用户当前浏览器的 active tab。

学习完成后继续输入：

```text
帮我进入工作台
```

如果你指定一个还没学过的页面，例如：

```text
帮我在 http://localhost:5176/orders 导出订单
```

系统应提示：

```text
还没学过这个站点或页面，需要先学习。
```

## 查看聊天历史和回复来源

`wagent chat` 启动后会显示本次会话 ID。你可以在 Console 的聊天历史页面查看：

```text
http://localhost:5174/conversation/history/<session_id>
```

当前 history 页面已经能查看消息、事件、已学操作、learning run、replay summary 和 raw JSON。

M11.3.4 的 Conversation Intake Agent 已实现后，这个页面会展示：

- 这条 WAgent 回复是代码生成、Agent 生成、混合生成还是未知来源。
- 如果是代码生成，会标注代码路径，例如 Conversation Orchestrator 或 Interactive Chat Runtime。
- 如果是 Agent / LLM 生成，会标注内部 Agent role、provider、model、request id 和 schema。
- 原始 LLM 记录会默认脱敏，不应展示密码、token 或访问口令明文。

真实 LLM-backed smoke 尚未记录前，不要把“真实 provider trace 一定存在”作为当前入门指南的通过条件。
如果本地没有配置 LLM provider，history 可能显示代码生成或 fallback。

## 第一步：教它进入工作台

在 `You >` 后输入：

```text
学习一下这个工作台登录页怎么进入，地址是 http://localhost:5176/workspace-login，操作员账号是 demo，访问口令是 123456
```

期望看到类似：

```text
WAgent > 我会打开浏览器学习：在工作台登录页输入操作员账号和访问口令，并点击“进入工作台”按钮。
WAgent > 学习完成：我学会了进入工作台操作。之后你可以说“帮我进入工作台”。
```

这里的意思是：系统已经知道要在工作台登录页输入操作员账号和访问口令，然后点击“进入工作台”按钮。

使用时只看这两类信息：

- 它有没有说明自己正在学习什么操作。
- 它有没有明确告诉你已经学会，以及之后可以怎么说。

## 第二步：让它进入工作台

继续输入：

```text
帮我进入工作台
```

期望看到：

```text
WAgent > 我会打开浏览器执行：输入操作员账号和访问口令，并点击“进入工作台”按钮。
WAgent > 进入工作台完成。
```

正常情况下，不应该出现要求你确认、输入编号，或看起来像代码 / 调试信息的内容。
例如：

```text
请确认
是否执行
输入确认
LearnedPath
replay
run_id
selector
className
```

如果出现这些内容，说明普通用户体验还不够好，需要记录下来。

## 第三步：说一个它还没学过的操作

继续输入：

```text
帮我在 http://localhost:5176/orders 导出订单
```

期望看到：

```text
WAgent > 还没学过这个站点或页面，需要先学习。
```

这里不需要系统猜页面，也不需要它跨站点拿其他 LearnedPath 执行。当前版本只需要清楚告诉用户：
这个站点或页面还没有学过。

## 退出

输入任意一个：

```text
exit
quit
:q
```

也可以按 `Ctrl+C`。

## 怎么判断这次使用是正常的

这次只看你能不能完成下面几件事：

1. 用户能进入 `wagent chat`。
2. 用户能用一句话教会系统工作台登录页操作。
3. 用户能用“帮我进入工作台”让系统执行刚学会的操作。
4. 用户指定一个没学过的页面时，系统能清楚说明“需要先学习”。

通过示例：

```text
WAgent > 我会打开浏览器学习：在工作台登录页输入操作员账号和访问口令，并点击“进入工作台”按钮。
WAgent > 学习完成：我学会了进入工作台操作。之后你可以说“帮我进入工作台”。
WAgent > 我会打开浏览器执行：输入操作员账号和访问口令，并点击“进入工作台”按钮。
WAgent > 进入工作台完成。
WAgent > 还没学过这个站点或页面，需要先学习。
```

不通过示例：

```text
WAgent > 找到 LearnedPath ...
WAgent > replay_run_id=...
WAgent > 点击 selector button.btn
WAgent > 请确认是否执行
WAgent > 请输入 session id
```

这些内容对普通用户来说太像开发调试信息。
