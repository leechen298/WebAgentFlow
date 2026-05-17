# 意图（Intent）

状态：proposed

## 目标

让 `wagent chat` 在学习和执行网页操作时默认打开用户可见的项目内置 Playwright
Chromium，并保留 headless opt-out，使普通用户能直接看到 WebAgentFlow 正在操作网页。

## 动机

M11.3 已经把入口从开发者命令 `wagent conversation send` 收束到产品入口
`wagent chat`，但当前操作过程对普通用户仍然像“后台任务”：CLI 会回复学习或执行结果，
用户却看不到真实浏览器、真实输入和真实点击。

对普通用户闭环来说，系统不仅要说“我会执行”，还要让用户能看到它正在打开页面并完成操作。
这能降低人工测试的不确定性，也让 `wagent chat` 更接近一个可直接体验的前台产品入口。

## 边界 / 非目标

- 本轮不把能力绑定到某个具体页面；页面级验收样例只放在 `test-plan.md`。
- 本轮不扩展自然语言意图理解、slot binding、多 path 歧义处理或 M12 recovery。
- 本轮不改变非 `interactive_chat` session 的 preview / confirmation / explicit replay 行为。
- 本轮不改用用户系统 Chrome，不接管浏览器 profile、cookie、扩展或已有标签页。
- 本轮不实现 streaming progress；CLI 仍然按同步请求返回。

## 成功标准

- `wagent chat` 默认以可见浏览器运行学习和执行。
- 用户可以通过 `wagent chat --headless` 选择后台运行。
- 学习和执行链路都使用项目已安装的 Playwright Chromium。
- `interactive_chat` 以外的 conversation / replay 入口保持默认 headless 行为。
- CLI 文案仍然面向普通用户，不暴露 selector、id、className、LearnedPath、run_id 或 replay id。
- 文档和测试计划明确区分“通用可见浏览器能力”和“当前人工验收页面样例”。
