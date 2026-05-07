# 10.6 · Cross-page pattern mining

## 执行前必读

本包当前是 draft only，不能直接施工。后续修订为可
执行状态前，请先阅读 `AGENTS.md`、`docs/product-model.md`、
`docs/iterations/m10/m10-plan.md`，再读本目录的 `intent.md`
和 `plan.md`。

状态：Draft only，不可直接施工。建议在 `10.2` replay 与主要控件
覆盖稳定后再开工。

## 目标

从多个 LearnedPath 中归纳 login / search / CRUD 等跨页面 action
pattern，作为后续 planner 的候选知识，而不是直接驱动浏览器。

## 动机

- 单条 LearnedPath 只能复用同一页面模板；实际产品还需要识别“不同
  页面共享同一操作形态”。
- pattern mining 应建立在已验证 / 已确认的数据上，避免运行时凭空
  编造路径。

## 边界（本轮不做）

- 不执行 browser replay；这是 `10.2`。
- 不新增自主探索策略。
- 不让 pattern 直接越过用户确认成为强信任路径。

## 成功标准

1. 能从 LearnedPath 集合中抽取稳定 pattern metadata。
2. 至少覆盖 login 和 search 两类基础 pattern。
3. pattern 来源可追溯到具体 LearnedPath / run。
4. 不使用未验证数据生成高信任 pattern。
