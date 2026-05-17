# 11.3.1 Visible Chat Browser Operation

状态：proposed
里程碑：M11
类型：code

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

混合型迭代按代码型迭代门禁处理。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - 可见浏览器运行、headless opt-out、CLI / session metadata 契约。
- `technical-design.md` - CLI、conversation runtime、learning / replay runtime config 传递设计。
- `test-plan.md` - 单元、集成、CLI、人工 smoke 和 live browser evidence 边界。
- `plan.md` - 实施步骤和验证命令。
- `review.md` - 评审记录、实际验证证据和未运行项。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [ ] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [ ] `review.md` 在收尾前记录验证证据。

## 当前状态

M11.3 已经提供 `wagent chat` 普通用户闭环：用户可以在交互式 CLI 里要求
WebAgentFlow 学习页面操作，再用自然语言执行已学操作。当前缺口是学习和执行虽然
由 Playwright Chromium 驱动，但默认运行在 headless 模式，普通用户看不到网页被打开、
输入、点击和跳转。

本包把 `wagent chat` 的产品入口体验调整为默认可见浏览器运行。能力本身不绑定具体
业务页面；具体页面只作为 `test-plan.md` 中的验收靶子。
