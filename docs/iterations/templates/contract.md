# 契约（Contract）

状态：proposed

## 概念 / 边界契约

<定义本轮新增或修改的概念。如果没有，写 `No concept changes` 并说明原因。>

## 状态 / 结果契约

<定义状态、枚举值、状态推导词和优先级。如果没有，写 `No state changes` 并说明原因。>

## Schema / API 契约

<定义 request、response、CLI、event 或存储数据语义。如果没有，写 `No schema/API changes` 并说明原因。>

## Evidence / Observation 契约

<定义允许的 evidence 来源、observation 来源和 verification 边界。如果没有，写 `No evidence changes` 并说明原因。>

## 产品模型 / 范围 / 路线图对齐（Product Model / Scope / Roadmap Alignment）

- Product model 对齐：<对齐说明，或 `N/A` + 原因>
- Scope boundary 对齐：<对齐说明，或 `N/A` + 原因>
- Roadmap / milestone 对齐：<对齐说明，或 `N/A` + 原因>
- 是否改变已有 product lifecycle / Agent role / milestone boundary：Yes / No
- 如果是 Yes，必须先更新哪些权威文档：<文档路径，或 `N/A` + 原因>

## 兼容性契约

<说明旧数据、旧 API response、旧行为如何继续有效。>

## 不变契约

本轮不改变：

- Product lifecycle stages：<不变，或说明必须先改哪个权威文档>
- Internal Agent roles：<不变，或说明必须先改哪个权威文档>
- Public API contracts：<不变，或说明变化>
- Database schema：<不变，或说明 migration>
- Replay status semantics：<不变，或说明变化>
- Reporter / recovery / abort boundaries：<不变，或说明变化>

## 非目标

- <本轮不改变的契约边界。>

## 未决问题

- <问题、负责人、决策截止点。>

不允许空白或隐式省略。只有写明原因时，才允许使用 `N/A`。
