# 技术设计（Technical Design）

状态：proposed

## 当前状态（Current State）

<当前已有代码、schema、service、测试和文档状态。>

## 合约对齐 / 不变量（Contract Alignment / Invariants）

`contract.md` 中每个关键状态、边界、兼容性规则和非目标，都必须映射到实现机制和测试入口。
无法映射时必须写出 `N/A` 和原因。

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| <contract rule> | <schema / service / check，或 `N/A` + 原因> | <测试层级或 `test-plan.md` 条目，或 `N/A` + 原因> | <风险 / 边界> |

## 实现方案（Proposed Implementation）

<本轮具体怎么实现。>

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | Yes / No |  |  |
| API response schema | Yes / No |  |  |
| Database schema / migration | Yes / No |  |  |
| CLI | Yes / No |  |  |
| Console UI | Yes / No |  |  |
| Conversation events | Yes / No |  |  |
| Replay execution | Yes / No |  |  |
| Reporter | Yes / No |  |  |
| Worker / async jobs | Yes / No |  |  |
| Tests / fixtures | Yes / No |  |  |
| Docs | Yes / No |  |  |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

<新增或修改哪些 schema、request / response 字段、migration；是否向后兼容。>

## 服务 / 模块设计（Service / Module Design）

<新增或修改哪些 service / module / function；输入输出是什么。>

## 数据流（Data Flow）

<从入口到输出的流程，包括中间 event、持久化状态或 artifact。>

## 状态推导（Status / State Derivation）

<状态如何推导，优先级是什么，fallback 行为是什么。>

## 兼容性（Compatibility）

<旧数据、旧 API response、既有调用方如何兼容。>

## 失败 / 边界情况（Failure / Edge Cases）

<空值、timeout、partial result、provider failure、stale data、unsupported state 怎么处理。>

## 非目标（Non-goals）

- <本轮明确不覆盖的实现范围。>

## 测试矩阵入口（Test Matrix）

这里只写高层测试入口，不写完整执行手册。复杂测试、E2E、live run、Codex / AI 外部测试操作员、
人工测试和跨层验证必须写入 `test-plan.md`。

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| <API unit / service integration / Console E2E / reporter evidence / recovery boundary> | <必须证明什么> | <`test-plan.md` 条目，或 `N/A` + 原因> |

## 验证命令入口（Validation Commands）

这里只列实现设计要求的最低验证命令。实际执行结果记录在 `review.md`；详细测试矩阵记录在
`test-plan.md`。

```bash
<command>
```
