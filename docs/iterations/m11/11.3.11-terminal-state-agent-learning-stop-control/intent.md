# 意图（Intent）

状态：proposed

## 目标

建立 M11.3 post-closeout 的 `Terminal State Agent / 终态判断 Agent`、终态证据与停止控制迭代路线，
让 L1 autonomous exploration 在 URL-only learning 和筛选页学习过程中能识别一次操作是否已经
到达可评价的终态，并把该终态证据交给 Attempt Evaluation Agent 和 LearnedPath ingest gate 使用。

成功状态：

- 父包明确终态判断的产品边界、证据来源、状态语义、Agent 边界和 live-run 停止规则。
- 父包把工作拆成多个可独立评审和实现的 child packages。
- 每个 planned child package 有完整 quasi-package spec，后续实现 Agent 不需要猜测 scope。
- M11 README 能发现本父包、当前 active child 和实现前置门禁。

## 动机

当前问题来自真实用户视角：URL-only learning 进入筛选页时，系统可能只沉淀“点击搜索按钮”，
而没有识别文本搜索、状态筛选、组合筛选等能力。更深层原因是探索循环不知道一次尝试何时
完成，也不知道“完成”到底意味着什么。

表单页和登录页常见终态比较明显，例如跳转、提交成功、记录创建成功。筛选页和业务工具页
更复杂：

- 搜索可能只触发列表接口和表格局部刷新。
- 刷新可能没有明显 DOM 差异，但网络请求和 loading 周期已经完成。
- 导出 / 下载的终态是浏览器 download event 和 artifact metadata。
- 弹窗、抽屉、popover、浏览器 dialog 可能是一次点击的终态。
- toast / message 可能短暂出现，需要及时捕获。

WebAgentFlow 控制自己的 Playwright / Chromium 浏览器，这是优势。M11.3 的当前修复应利用浏览器事件、
网络事件、DOM 稳定性、下载事件和页面理解结果共同判断终态，而不是只靠点击后截图差异或
探索结束后的 Supervisor 汇总。

## 产品模型对齐

本轮放在 M11.3 post-closeout，因为问题来自当前 `wagent chat` / URL-only learning /
`/users` 筛选页学习闭环，而不是未来独立 M14 campaign。`docs/product-model.md` 和
`docs/roadmap.md` 把完整 Page Understanding / Attempt Evaluation / Learning Report 质量体系放在
M14；本包只把其中与当前学习失败直接相关的终态判断能力前置为 M11.3 修复包，并记录未来 M14
应复用该基础。

本包不新增 product lifecycle stage，不新增 legacy Agent 字母。`Terminal State Agent /
终态判断 Agent` 是 proposed M11.3 L1 Agent role：它不替代 Page Understanding Agent 或 Attempt
Evaluation Agent，而是在两者之间判断“当前 attempt 是否已到可评价终态”。第一个子包必须先
把这个新 Agent 边界写入 / 复核 `docs/product-model.md` 和 child contract，之后才能进入运行时实现。

## 边界

本父包不做运行时代码，不改 schema，不改 API，不改 CLI，不改 Console，不运行 live autonomous
validation。

本轮不做：

- 不让 LLM 逐步控制浏览器。
- 不把终态判断写成 target-specific `/users` 规则。
- 不为了第一版直接 fork 或修改 Chromium；先使用 Playwright / CDP / browser context 能力，
  只有子包证明确有不可观测缺口时再另开浏览器改造方案。
- 不把失败或证据不足的 attempt 沉淀为成功 LearnedPath。
- 不替代 M12 recovery / retry / abort。

## 成功标准

- `docs/iterations/m11/README.md` 存在并列出 11.3.11。
- 父包八个文档存在：`README.md`、`intent.md`、`contract.md`、`test-plan.md`、`plan.md`、
  `review.md`、`GOAL_RUNNER.md`、`CURRENT_STATE.md`。
- `plan.md` 为所有 planned child packages 写明 package name、status、type、goal、
  why、required reading、allowed / forbidden changes、deliverables、tests、compatibility、
  guardrails、exit criteria、handoff。
- `contract.md` 明确 terminal state taxonomy、terminal outcome、evidence strength、
  stop decision、Terminal State Agent 边界、LearnedPath gate 和 live-run boundary。
- `CURRENT_STATE.md` 指向 child 1 文档生成，不允许跳过 child docs 直接实现。
