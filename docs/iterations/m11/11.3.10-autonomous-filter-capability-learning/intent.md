# 意图（Intent）

状态：proposed

## 目标

把 URL-only product-level learning 从“只点击一个搜索按钮并误报为学会开始操作”
修正为两阶段能力：先自主探索并沉淀筛选页 capability LearnedPaths，再基于学习结果向
用户反馈成功、部分成功、失败或未验证。

## 动机

用户在 `http://127.0.0.1:5177/users` 上触发学习后，系统实际只持久化了
`#btn-search` click + observe，却反馈“我学会了开始操作，之后你可以说帮我开始”。
这说明当前 runtime chat 把 learning confirmation 当成业务意图，并且 L1 autonomous
learning 没有为筛选页生成单字段 / 组合筛选场景。

按产品模型，WebAgentFlow 的核心不是让用户背诵固定口令，而是先学习页面操作能力，
再让用户直接说要做的工作。因此必须先补自主探索能力，再补学习结果反馈门禁。

## 边界 / 非目标

- 本父包不直接改运行时代码；代码实现只允许在子包中进行。
- 本轮不实现完整任意网页全量操作发现；当前聚焦筛选 / 搜索类页面 capability。
- 本轮不做指数级组合爆炸；默认采用单字段全覆盖、pairwise 组合和一个 all-supported
  smoke。
- 本轮不把 `/users`、字段名、按钮文案、fixture 数据硬编码进产品 runtime 或 prompt。
- 本轮不运行 live autonomous validation；如需 live run，必须由后续线程显式授权。

## 成功标准

- 父包文档完整，包含 `GOAL_RUNNER.md` 和 `CURRENT_STATE.md`。
- M11 README 能发现父包和两个子包，并标明当前 active child。
- 子包 1 七件套定义 filter capability discovery、scenario matrix、run history 和
  LearnedPath ingest gate。
- 子包 2 七件套定义 learning outcome gate、用户反馈规则和控制词过滤。
- 父包 `CURRENT_STATE.md` 指向子包 1，并禁止跳过子包 1 直接实现子包 2。
