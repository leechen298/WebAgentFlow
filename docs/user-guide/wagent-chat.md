# wagent chat 入门指南

这份文档面向第一次使用 WebAgentFlow 的普通用户。它只说明怎么打开
`wagent chat`、怎么输入一句话、怎么看系统回复。

## 你能用它做什么

`wagent chat` 是一个命令行聊天入口。你可以用自然语言告诉 WebAgentFlow：

- 学习你提供的网页怎么操作。
- 执行当前会话或历史记录里已经学会的网页操作。

WebAgentFlow 不内置人工测试目标。测试者需要在对话里提供目标页面 URL、
操作描述和必要输入；不要把某个测试站点、测试页面或测试数据当成产品默认知识。

当前版本建议一次说清楚页面地址、要学习或执行的操作，以及必要输入。如果一句话里
没有提供页面地址或必要输入，系统可能无法像真正的对话 Agent 一样继续追问和续接。

Conversation Intake Agent / 对话理解 Agent 会把普通用户的话理解成结构化的操作意图、
目标页面、输入槽位和缺失信息。这个能力不是让 LLM 控制浏览器，而是让 LLM 理解用户
说的话；真正学习和执行仍由 WebAgentFlow 的 Learning / Replay 服务完成。如果本地
没有配置 LLM provider，系统可能走 deterministic fallback。

聊天历史调试页在
`http://localhost:5174/conversation/history/<session_id>` 中显示消息、事件、已学操作、
learning run、replay summary 和 raw JSON。Codex CLI 只是外部测试或调试操作者，
不会被当成 WebAgentFlow 内部回复者。

## 测试目标边界

`wagent chat` 只应该学习用户输入的页面地址，并只执行当前会话或历史记录里已经学过的
站点 / 页面 / 操作。如果你要求它操作一个还没学过的站点或操作，它应该清楚告诉你需要
先学习，或询问下一步，而不是猜测测试目标或跨站点复用别的 LearnedPath。

主仓库不再提供内置的产品测试站点。人工测试时，目标页面由测试操作者自行选择和启动，
再通过聊天输入传给 `wagent chat`。工程验证用的 fixture、`verify-scenario`、
专项验证计划和普通 `wagent chat` 入门使用是不同测试面，不要混在一起判断。

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

看到 console、api、worker 都正常启动后，就可以开始测试。CLI 调用的默认 API 地址是
`http://localhost:8001`；如果 API 用了别的端口，启动 `wagent chat` 时传
`--api-base`。

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
WAgent > 本次会话 ID：<session_id>。需要调试时可以在管理后台查看。
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

如果你不想看到浏览器窗口，可以使用后台运行：

```bash
.venv/bin/wagent chat --headless
```

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

当前版本默认会打开 Playwright Chromium，你可以看到页面加载、输入、点击和跳转。

## 输入模板

先选择一个你要测试的、当前机器能访问的页面。这个页面不应该来自 WebAgentFlow 的默认配置，
而应该由测试操作者明确提供。

在 `wagent chat` 中输入时，把占位符替换成测试操作者选择的目标和安全测试数据：

```text
学习这个页面上的“<操作名称>”操作，地址是 <目标页面 URL>，需要用到的输入是：<字段1>=<值1>，<字段2>=<值2>
```

当前版本建议尽量一次说清楚页面地址和必要输入。

学习完成后继续输入：

```text
帮我执行刚才学会的“<操作名称>”，这次使用：<字段1>=<新值1>，<字段2>=<新值2>
```

如果要检查未知页面或未知操作边界，可以输入：

```text
帮我在 <另一个未学过的目标页面 URL> 上执行 <操作名称>
```

系统应提示还没学过，需要先学习或补充目标信息。它不应该猜测你的测试目标，也不应该拿别的
页面路径去执行。

## 查看聊天历史和回复来源

`wagent chat` 启动后会显示本次会话 ID。你可以在 Console 的聊天历史页面查看：

```text
http://localhost:5174/conversation/history/<session_id>
```

也可以用 CLI 查看：

```bash
.venv/bin/wagent conversation history <session_id> --pretty
.venv/bin/wagent conversation events <session_id> --pretty
.venv/bin/wagent conversation messages <session_id> --pretty
```

当前 history 页面已经能查看消息、事件、已学操作、learning run、replay summary 和 raw JSON。

历史页面会展示：

- 这条 WAgent 回复是代码生成、Agent 生成、混合生成还是未知来源。
- 如果是代码生成，会标注代码路径，例如 Conversation Orchestrator 或 Interactive Chat Runtime。
- 如果是 Agent / LLM 生成，会标注内部 Agent role、provider、model、request id 和 schema。
- 原始 LLM 记录会默认脱敏，不应展示密码、token 或访问口令明文。

真实 LLM-backed smoke 尚未记录前，不要把“真实 provider trace 一定存在”作为当前入门指南的通过条件。
如果本地没有配置 LLM provider，history 可能显示代码生成或 fallback。

## 第一步：教它一个操作

在 `You >` 后输入：

```text
学习这个页面上的“<操作名称>”操作，地址是 <目标页面 URL>，需要用到的输入是：<字段1>=<值1>，<字段2>=<值2>
```

使用时只看这两类信息：

- 它有没有说明自己正在学习什么操作。
- 它有没有明确告诉你已经学会，以及之后可以怎么说。

## 第二步：让它执行已学操作

继续输入：

```text
帮我执行刚才学会的“<操作名称>”，这次使用：<字段1>=<新值1>，<字段2>=<新值2>
```

判断重点是：系统应说明正在执行已学操作；执行结束后，应给出面向用户的完成说明，
并能把结果和页面证据或目标值关联起来。

正常情况下，不应该出现要求普通用户理解的代码 / 调试信息。例如：

```text
LearnedPath
replay_run_id
selector
className
slot_overrides
execution_evidence
```

如果出现这些内容，说明普通用户体验还不够好，需要记录下来。

## 第三步：说一个它还没学过的操作

继续输入：

```text
帮我在 <另一个未学过的目标页面 URL> 上执行 <操作名称>
```

这里不需要系统猜页面，也不需要它跨站点拿其他 LearnedPath 执行。当前版本只需要清楚告诉用户：
这个站点、页面或操作还没有学过。

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
2. 用户能把测试操作者提供的页面 URL、操作描述和必要输入交给系统。
3. 用户能用一句话教会系统一个页面操作。
4. 用户能让系统执行刚学会的操作，且不会暴露内部调试细节。
5. 用户指定一个没学过的页面或操作时，系统能清楚说明需要先学习或补充目标信息。

不通过信号：

```text
WAgent > 找到 LearnedPath ...
WAgent > replay_run_id=...
WAgent > 点击 selector button.btn
WAgent > slot_overrides=...
WAgent > 请输入 session id
```

这些内容对普通用户来说太像开发调试信息。
