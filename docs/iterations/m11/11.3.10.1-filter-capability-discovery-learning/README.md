# 11.3.10.1 Filter Capability Discovery Learning

状态：PACKAGE_COMPLETE
里程碑：M11.3 post-closeout
类型：code / mixed
父包：`11.3.10-autonomous-filter-capability-learning`

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [x] 混合型迭代

本包是 `11.3.10` 的第一个 executable child package。它修复的不是一句
`wagent chat` 回复文案，而是 URL-only learning 在筛选页上缺少页面能力发现和场景矩阵，
导致只沉淀“点击搜索按钮”这类无业务语义 LearnedPath 的问题。

## 背景判断

之前登录页验证正常，不能说明当前 `/users` URL-only learning 没有问题。两者入口不同：

- 登录页验证通常是 spec-backed / scenario-backed，自带目标、输入和验证预期。
- 当前问题来自 product-level URL-only learning，用户只给 URL 并确认学习，系统需要自己发现页面能力。

因此本包目标是让 L1 autonomous learning 在没有 authored spec 的筛选页上，仍能发现筛选控件、
生成可审计场景、执行场景，并把通过证据门禁的能力沉淀为 LearnedPath。

## 文档集

- `README.md` - 包索引、状态、范围。
- `intent.md` - 用户问题、产品目标、成功状态。
- `contract.md` - capability discovery / scenario / evidence / LearnedPath contract。
- `technical-design.md` - 服务、数据流、适配器、持久化和影响面设计。
- `test-plan.md` - unit / integration / API / regression / live-run 边界。
- `plan.md` - 代码实现顺序和 checkpoint。
- `review.md` - 设计复核、implementation authorization 和验证记录。

## 成功状态

URL-only learning 面对 `/users` 这类筛选页时，不再只生成一个 `#btn-search`
LearnedPath。系统应产生多条可审计 filter capability scenario：

- 每个支持筛选控件的单字段搜索场景。
- 默认 pairwise 组合搜索场景。
- 一个 all-supported smoke 场景。
- 每个场景有独立 autonomous run history。
- 只有通过证据门禁的场景进入 LearnedPath。

## Closeout Summary

本包已完成非 live runtime implementation。已落地 target-agnostic
`PageCapabilityDiscovery` / `FilterCapability` / `CapabilityScenario`，并通过
repo-local tests 验证：

- URL-only filter learning 会生成 single / pairwise / all-supported smoke 场景。
- `/users` 形状的 9 个筛选控件会生成 46 个候选场景。
- 每个 capability scenario 会写入可追踪 discovery batch / scenario metadata。
- LearnedPath 只从有绑定动作证据的场景沉淀；只点击搜索按钮的场景不会进入 LearnedPath。

Live autonomous validation 默认未运行，等待用户明确授权。

## 非目标

- 不为 `/users` 或任何具体 fixture 页面硬编码字段、按钮文案或测试数据。
- 不做所有字段组合的指数级全排列。
- 不新增产品 lifecycle stage 或内部 Agent role。
- 不实现 `wagent chat` 用户反馈门禁；该工作属于
  `11.3.10.2-learning-outcome-gate-chat-feedback`。
- 不在文档阶段执行 live autonomous run。
