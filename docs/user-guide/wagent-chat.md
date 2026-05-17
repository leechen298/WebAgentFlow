# wagent chat 入门指南

这份文档面向第一次使用 WebAgentFlow 的普通用户。它只说明怎么打开
`wagent chat`、怎么输入一句话、怎么看系统回复。

## 你能用它做什么

`wagent chat` 是一个命令行聊天入口。你可以用自然语言告诉 WebAgentFlow：

- 学习某个网页怎么操作。
- 执行已经学会的网页操作。

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

## 第一步：教它怎么登录

在 `You >` 后输入：

```text
学习一下这个登录页怎么登录，地址是 http://localhost:5175/login
```

期望看到类似：

```text
WAgent > 我会学习：在登录页输入账号密码，并点击“登录”按钮。
WAgent > 学习完成：我学会了登录页的登录操作。之后你可以说“帮我登录”。
```

这里的意思是：系统已经知道要在登录页输入账号密码，然后点击“登录”按钮。

使用时只看这两类信息：

- 它有没有说明自己正在学习什么操作。
- 它有没有明确告诉你已经学会，以及之后可以怎么说。

## 第二步：让它登录

继续输入：

```text
帮我登录
```

期望看到：

```text
WAgent > 我会执行：输入账号密码，并点击“登录”按钮完成登录。
WAgent > 登录完成。
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
帮我导出报表
```

期望看到：

```text
WAgent > 我会执行：导出报表。
WAgent > 还没学过这个操作，需要先学习。
```

这里不需要系统猜页面，也不需要它追问用户。当前版本只需要清楚告诉用户：
这个操作还没有学过。

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
2. 用户能用一句话教会系统登录页操作。
3. 用户能用“帮我登录”让系统执行登录。
4. 用户说一个没学过的操作时，系统能清楚说明“需要先学习”。

通过示例：

```text
WAgent > 我会学习：在登录页输入账号密码，并点击“登录”按钮。
WAgent > 学习完成：我学会了登录页的登录操作。之后你可以说“帮我登录”。
WAgent > 我会执行：输入账号密码，并点击“登录”按钮完成登录。
WAgent > 登录完成。
WAgent > 我会执行：导出报表。
WAgent > 还没学过这个操作，需要先学习。
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
