# Intent

## Problem

WebAgentFlow 已具备原子 `LearnedCapability` 和底层 `CapabilityComposer`，但产品还不能自动把
页面上已经学到的可操作组件组合成候选路径，再通过真实执行反馈决定是否沉淀为可靠
`LearnedPath`。

这导致 Validation Site 即使能定义确定性 oracle，也只能评估已存在的原子能力和手工/自主学习
产生的路径，无法系统评估“WebAgentFlow 基于已学组件能组合出哪些合理路径”。

## Goal

实现前的设计目标：

- 定义自动组合候选生成的 bounded 策略。
- 定义 composition candidate 的状态、风险、覆盖率和 evidence。
- 定义候选执行与 promotion gate。
- 定义 failed / rejected candidate 的 negative evidence。
- 定义面向外部 provider 的 redacted evidence bundle，支持 Validation Site 计算覆盖率和可靠性指标。

## User-Visible Product Intent

用户不需要知道组合细节。用户说自然工作需求时，WebAgentFlow 可以：

- 优先使用已有可靠 `LearnedPath`；
- 没有合适路径时，尝试由已学原子能力组合候选；
- 真实执行并验证；
- 成功后可沉淀为新 `LearnedPath`；
- 失败时诚实说明失败或需要教学，不宣称已学会。

## Non-Goals

本包不设计：

- 全排列穷举所有组件组合；
- 跨站点或跨页面复杂工作流组合；
- LLM 直接输出 Playwright 步骤；
- 未执行就持久化成功 `LearnedPath`；
- 使用 Validation Site 私有 oracle 参与 WebAgentFlow runtime 决策；
- live validation。

## Success Criteria For Docs

- 明确现有 11.3.12.4 composer 与本包新增链路的差异。
- 明确组合候选不等于 LearnedPath。
- 明确覆盖率类指标，而不是只凭人工感觉评估。
- 明确 promotion 必须走真实 execution evidence。
- 明确 Validation Site oracle 只在 provider 侧评估，WebAgentFlow 只导出 redacted evidence bundle。
