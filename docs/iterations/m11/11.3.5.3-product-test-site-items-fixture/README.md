# 11.3.5.3 · Product Test Site `/items` Fixture

状态：draft_docs（待评审，未开始实现）
里程碑：M11
类型：code
父迭代：[`11.3.5-customer-facing-agent-router-skill-runtime`](../11.3.5-customer-facing-agent-router-skill-runtime/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

混合型迭代按代码型迭代门禁处理。

## 迭代定位

11.3.5.3 是 working runtime P0 闭环的第一个子包。它只在
`apps/product-test-site` 新增一个稳定的 `/items` 列表页，为后续
11.3.5.4 参数化 learning / replay、11.3.5.5 ExecutionEvidence + Reporter
和 11.3.5.6 闭环测试提供页面基座。

本包不改 `wagent chat`、不改 replay、不采集 evidence、不接 TaskResultReporter。
它只证明 product-test-site 里存在一个可打开、可新增项目、可通过稳定 DOM anchor
观察结果的页面。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - `/items` 页面、稳定锚点、前端本地状态和非目标 contract。
- `technical-design.md` - Vue 页面、router 接入、状态模型和实现细节。
- `test-plan.md` - 文档检查、build、页面 smoke 和边界验证矩阵。
- `plan.md` - 实现步骤、验证命令和交付清单。
- `review.md` - 评审记录、文档阶段状态和后续 implementation review 入口。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [ ] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 已记录文档阶段边界和实现前检查项。
- [ ] 实现阶段已完成。
- [ ] `/items` 页面 build / smoke evidence 已记录到 `review.md`。

## 当前状态

文档包已生成，等待评审后进入实现。实现时只允许触及 product-test-site 页面基座：

```text
apps/product-test-site/src/pages/ItemsPage.vue
apps/product-test-site/src/router/index.ts
```

如确实需要补少量 product-test-site 专属测试文件，也必须保持在本包范围内。

本包验收完成后，11.3.5.4 才能基于 `/items` 场景实现 `item_name` slot、
`value_slot` 和 `slot_overrides`。
