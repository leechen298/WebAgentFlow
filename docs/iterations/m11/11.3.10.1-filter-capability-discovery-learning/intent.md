# Intent

## 用户问题

用户在 `wagent chat` 中输入 `http://127.0.0.1:5177/users` 并确认学习后，系统反馈：

- “学习完成：我学会了开始操作。”
- “之后你可以说‘帮我开始’。”

实际沉淀的能力只有类似点击搜索按钮的动作，没有学习页面上的筛选项，也没有形成单字段搜索、
组合搜索等可复用路径。这让普通用户无法理解“学会了什么”，也说明 L1 autonomous learning
在 product-level URL-only 入口下没有完成页面能力发现。

## 为什么不是“自主探索完全失效”

用户之前验证登录页时能正常通过，是合理的历史现象。登录页验证一般有明确 scenario、
输入值和预期结果，属于 spec-backed / scenario-backed autonomous run。当前问题是另一个入口：

1. 用户只给 URL。
2. 系统要求自己判断页面上可学习的能力。
3. 当前 runtime 把学习退化成了 generic goal 下的单个按钮路径。

所以本包修复的是 URL-only learning 对筛选页的 product-level capability discovery，
不是否定已有 spec-backed autonomous exploration。

## 产品目标

对 `/users` 这类筛选页，URL-only learning 应该自动发现页面上的筛选能力：

- 识别支持的筛选控件。
- 为每个筛选控件生成单独搜索场景。
- 生成默认 pairwise 组合搜索场景。
- 生成一个 all-supported smoke 场景。
- 为每个场景保留 autonomous run history。
- 只有 clean pass / evidence gate 通过的场景才能沉淀为 LearnedPath。

## 成功定义

本包成功后，学习完成状态不再等同于“找到并点击了一个搜索按钮”。成功状态应是：

- 页面分析能够产出 filter capability inventory。
- scenario generator 能从 inventory 产出 stable capability scenario matrix。
- 每个 scenario 的 run metadata 可审计、可追溯到同一 discovery batch。
- LearnedPath 的 identity 和 actions 指向具体筛选能力，而不是笼统
  `product_level` 或无语义 click。
- 回归测试证明 URL-only `/users` 不再只生成一个 `#btn-search` LearnedPath。

## 用户价值

普通用户不需要理解“页面学习”的内部机制，也不需要教系统逐个点击筛选项。用户只需确认学习，
系统应自动把页面上能操作的筛选能力学出来。后续 `wagent chat` 才能诚实告诉用户：

- 我学到了哪些搜索能力。
- 哪些能力暂时没有学会。
- 你可以直接告诉我想做什么工作。

该反馈门禁属于 child 2，本包只负责让 child 2 有真实 capability outcome 可以总结。
