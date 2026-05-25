# 意图（Intent）

状态：proposed

## Problem Statement

当前 WAgent 能完成一次外部 product-like 页面的教学流程，但无法稳定把教学中的业务目标变成可复用的 action identity。

在 2026-05-25 外部黑盒验证中，用户教了：

```text
Learn how to create an inventory item with SKU NB-ALP-001,
name Alpine Notebook, category Stationery, and stock quantity 24.
```

intake 已识别业务目标：

```text
action.goal = Create inventory item
canonical_goal = create_inventory_item
business object = inventory item
```

但学习完成后 session learned action 保存为：

```text
alias = Learn how to create
utterances = 帮我Learn how to create / Learn how to create 一下
```

随后用户用新值请求同一业务动作：

```text
Create an inventory item with SKU MUG-SKY-014,
name Skyline Mug, category Office, and stock quantity 18.
```

WAgent 没有匹配到已学 action，回复“还没学过你要做的这个操作”。这意味着 learn-then-execute 的产品闭环在外部黑盒验证中断裂。

## User-facing Impact

用户刚教过“创建库存项”，下一句要求“创建另一个库存项”，系统却认为自己没有学过这个操作。

这种体验会破坏 M11.3 runtime chat productization 的核心承诺：用户不应该关心内部 LearnedPath、session action、replay hook 或 matcher 的实现细节。用户的心智模型是：

```text
我教过你创建库存项，所以你应该能用新参数创建另一个库存项。
```

如果系统只记住“Learn how to create”这种教学句式，而没有保留“create inventory item”这个业务动作，用户会认为学习功能不可靠。

## Product Principle

学习结果必须保留用户真正要做的业务动作，而不是保留教学句式。

Bad：

```text
Learn how to create
```

Good：

```text
Create inventory item
create_inventory_item
create inventory item
```

教学包装词可以帮助识别 learn intent，但不应该成为可复用 action identity。可复用 action identity 应该来自 business goal、canonical goal、business object 和稳定 aliases；slot values 用于执行参数，不应该污染 action identity。

## Boundary

本迭代只修 runtime chat learning / execution 语义链路中的 11.3 外部黑盒验证缺口。

本迭代不做：

- 不启动 M12 recovery / retry / abort / interruption。
- 不解决复杂多页自动探索。
- 不实现完整 L1 page-wide automatic capability discovery。
- 不实现 L2 guided teaching 或 Teaching Guide Agent。
- 不处理登录、删除、支付、权限、跨站授权等高风险业务域。
- 不迁移或修改外部站点。
- 不恢复主仓库内嵌 test site。
- 不把旧 `5176/items` eval 重新作为 active 默认 eval。

## Success Definition

11.3.8 完成后，应满足：

- 学习 `create inventory item` 后，session action metadata 保留业务目标。
- suggested utterances 包含业务对象，而不是只保留 `Learn how to create`。
- 执行 `Create an inventory item with new values` 能匹配到已学 action。
- matcher 不会因为共享动词而执行错误 action。
- ambiguous learned actions 要求用户选择，不能自动猜。
- focused unit / service / integration-ish tests 通过。
- external black-box revalidation 至少重跑 `PV-CLI-002`、`PV-CLI-003`、`PV-CLI-004`、`PV-INTEGRITY-001`、`PV-INTEGRITY-002`。
- 最新 validation report 如实记录 `PASS` / `FAIL` / `FOLLOW_UP`，不隐藏失败。

## Why Now

M11 runtime final closeout已经明确：受控 runtime eval 和 first-wave user-facing behavior gates 通过，但 full learn-then-execute、page-wide automatic capability discovery、Console UI smoke 和 external black-box validation 不包含在已通过范围内。

外部黑盒验证现在给出了具体失败路径和 triage 证据。它不是一个抽象的未来能力，而是 M11.3 产品化收口中已经暴露出来的语义断链。因此应在 M11.3 下开 `11.3.8` 修复包，而不是把问题推迟到 M12 recovery。
