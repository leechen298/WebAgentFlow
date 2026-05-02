# 实施计划

状态：Draft only，不可直接施工。执行前需要等 `10.2` 和主要控件
迭代结果稳定。

## 执行前必读与硬约束

修订成本轮可执行计划前，请先读 `AGENTS.md`、`docs/product-model.md`、
`docs/iterations/phase-10/phase-plan.md`，再读本目录的 `intent.md`
和 `plan.md`。

本包转为可执行前，不得直接施工；施工时只做 `10.6`，不新增后续
Phase 项。

## 预期触及的模块

- LearnedPath repo / service：读取 confirmed / provisional 样本。
- 新 pattern service / schema：保存或临时产出 pattern metadata。
- console：可后置，仅在需要人工查看 pattern 时补入口。

## 粗粒度步骤

1. 定义 pattern 的最小数据结构：类型、来源、关键 action shape、
   confidence / trust 来源。
2. 从 login / search 样本开始做规则归纳。
3. 建立来源追溯：pattern 必须能回到具体 LearnedPath / run。
4. 补 service 单测，避免 pattern 从低信任或不完整样本生成。

## 执行前需要确认

- pattern 是否需要持久化表，还是先作为计算结果输出。
- confidence / trust 是否复用 LearnedPath trust，还是独立枚举。

## 验证方向

- 单测覆盖归纳、过滤、来源追溯。
- 本轮原则上不需要 live autonomous run。
