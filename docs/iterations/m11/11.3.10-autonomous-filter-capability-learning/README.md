# 11.3.10 Autonomous Filter Capability Learning

状态：children_complete_live_validation_not_run
里程碑：M11.3 post-closeout
类型：umbrella / campaign

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [ ] 混合型迭代
- [x] Umbrella / campaign planning package

本包只定义父级路线和子包边界，不直接授权 runtime implementation。运行时代码必须从
子包文档开始，且遵守子包 `review.md` 中的 `implementation_authorized` 状态。

## 迭代文档

- `README.md` - 父包索引、状态和 child route。
- `intent.md` - 总目标、动机、边界和成功标准。
- `contract.md` - 父级概念、证据、child sequencing 和 live-run 边界。
- `plan.md` - 两个 child package 的 execution-grade planned package spec。
- `review.md` - 父包文档评审、状态和后续 route。
- `GOAL_RUNNER.md` - Codex App `/goal` campaign 路由契约。
- `CURRENT_STATE.md` - 当前 active child 和 package queue。

## 子包

| Package | Type | Status | Route |
|---|---|---|---|
| `11.3.10.1-filter-capability-discovery-learning` | code / mixed | PACKAGE_COMPLETE | non-live implementation complete |
| `11.3.10.2-learning-outcome-gate-chat-feedback` | code / mixed | PACKAGE_COMPLETE | non-live implementation complete |

## 当前状态

用户反馈显示：`wagent chat` URL-only learning 在 `/users` 这样的筛选页上只学到
“点击搜索按钮”，随后又把 CLI 控制选项“开始学习”错误反馈成“帮我开始”。这暴露的根因
不是单一文案，而是 L1 autonomous learning 没有产出页面筛选能力场景库，后续
learning outcome 也缺少成功 / 失败门禁。

本父包将修复拆成两个阶段：

1. 先让自主探索发现筛选能力、生成场景、执行场景、留下 run history，并把 clean pass
   场景沉淀为 LearnedPath。
2. 再让 `wagent chat` 根据学习结果判断 success / partial_success / failed /
   unverified，并给用户诚实反馈。

两个 child package 均已完成非 live implementation 和 repo-local verification。
真实 `/users` live autonomous validation 仍未运行，等待用户明确授权。
