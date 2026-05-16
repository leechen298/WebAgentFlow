# 意图（Intent）

状态：accepted（manual smoke passed）

## 目标

让普通用户通过 `wagent chat` 完成最小闭环：学习 validation-site 登录页操作，
沉淀 LearnedPath，然后用“帮我登录”直接执行刚学到的路径并获得简洁结果。

## 动机

当前能力已经拆散存在：Workbench / autonomous exploration 可以学习页面，
LearnedPath 可以持久化，Conversation 可以接收任务，replay 可以执行路径。
但这些入口仍偏开发者视角，普通用户需要理解 session id、`conversation send`、
Workbench、LearnedPath、preview、confirm 等概念。

M11.3 要把这些底座能力装成第一个真正面向普通用户的 CLI 驾驶舱：
用户只面对 `wagent chat`，系统内部决定是学习还是执行。

## 边界 / 非目标

- 不做 `/users`、真实业务页面或多页面 workflow。
- 不做 M12 recovery / retry / abort / takeover / 异常沟通。
- 不做复杂 LLM 意图理解、teaching mode、按钮高亮、复杂 slot binding。
- 不废除 11.1.5 confirmation gate；只给 `interactive_chat` happy path 开自动执行旁路。
- 不让 LLM 逐步控制浏览器，不做 hidden relearning，不读取 raw HTML 临场规划。

## 成功标准

- `wagent chat` 是顶层 CLI 命令，启动后自动创建 conversation session。
- session 创建时设置 `current_mode=interactive_chat`，并写入 `metadata.client=wagent_chat`、
  `metadata.runtime_policy=auto_execute_happy_path`。
- 用户输入“学习一下这个登录页怎么登录，地址是 http://localhost:5175/login”后，
  系统触发学习，真实沉淀 LearnedPath，并反馈后续可以说“帮我登录”。
- 用户输入“帮我登录”后，系统只从当前 session learned actions 命中路径并直接 replay。
- 普通成功路径不出现确认门槛，不要求输入“确认”或“执行”。
- 用户输入未学过任务时只提示“还没学过这个操作，需要先学习。”
- 非 `interactive_chat` session 继续走现有 preview / confirmation / execution 逻辑。
