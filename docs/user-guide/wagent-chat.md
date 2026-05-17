# wagent chat 入门指南

这份文档面向第一次使用 WebAgentFlow 的普通用户。它只说明怎么打开
`wagent chat`、怎么输入一句话、怎么看系统回复。

## 你能用它做什么

`wagent chat` 是一个命令行聊天入口。你可以用自然语言告诉 WebAgentFlow：

- 学习某个网页怎么操作。
- 执行已经学会的网页操作。

当前版本先支持登录页：

```text
http://localhost:5175/login
```

## 启动前准备

先在一个终端启动 WebAgentFlow：

```bash
cd /Users/leechen/projects/WebAgentFlow/v0.1
pnpm run dev
```

看到类似下面的地址后，就可以开始测试：

```text
console: http://localhost:5174
validation-site: http://127.0.0.1:5175
api: http://0.0.0.0:8001
```

如果 `pnpm run dev` 没有正常启动，先不要继续测试，先解决启动问题。

## 进入聊天

另开一个终端：

```bash
cd /Users/leechen/projects/WebAgentFlow/v0.1
source .venv/bin/activate
wagent chat
```

你应该看到：

```text
WAgent > 你好，我可以学习页面操作，也可以执行已经学会的操作。
You >
```

如果提示 `wagent: command not found`，说明当前终端还没有进入项目环境，重新执行：

```bash
source .venv/bin/activate
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
