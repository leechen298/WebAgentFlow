# 契约（Contract）

状态：proposed

## 概念 / 边界契约

本父包新增一个两阶段修复路线，不新增 product lifecycle stage 或 internal Agent role。

- `FilterCapabilityDiscovery`：从 PageAnalysis 和执行观察中发现筛选页可学习能力的
  L1 autonomous learning 子流程。它是 learning pipeline 的能力发现阶段，不是
  L3 Task Path Planner。
- `FilterCapability`：一个可独立学习、验证和复用的筛选能力，例如按文本字段搜索、
  按状态筛选、按日期范围筛选或多个筛选条件组合。
- `CapabilityScenario`：一个可审计自主探索场景。每个 scenario 必须有稳定 id、
  scenario kind、输入绑定、预期观察目标、run history 和 outcome。
- `LearningOutcomeGate`：把一个 learning batch 的多个 scenario 结果归并成用户可理解的
  success / partial_success / failed / unverified。

父包只规定这两个子包的顺序。子包 1 负责能力发现和 LearnedPath 沉淀；子包 2 负责
learning outcome 和 chat feedback。子包 2 不得替代子包 1 的能力发现。

## 状态 / 结果契约

父包状态：

- `docs_generated_pending_review`：父包和子包文档已经生成，等待复核。
- `active_child_1_ready`：子包 1 文档已审核，可进入子包 1 implementation。
- `child_1_complete_child_2_ready`：子包 1 完成，子包 2 可进入 implementation。
- `PACKAGE_COMPLETE`：两个子包均完成并通过 closeout。
- `BLOCKED` / `NEEDS_USER_INPUT`：文档、证据或 scope 冲突导致停止。

子包顺序不可交换。没有子包 1 的 capability summaries 和 outcome schema，子包 2
不得实现 runtime feedback。

## Schema / API 契约

父包本身不定义最终 schema wire shape。子包 1 和子包 2 必须在各自 `contract.md` /
`technical-design.md` 中定义具体 schema、event、history response 或 storage changes。

父包要求：

- 子包 1 的 discovery batch / capability scenario metadata 必须可被 run history 审计。
- 子包 2 的 learning outcome 必须可被 `wagent chat` 和 Conversation History detail 消费。
- 所有新增 schema 必须向后兼容；旧调用方忽略新增字段仍可工作。

## Evidence / Observation 契约

允许作为学习证据的来源：

- autonomous run history；
- PageAnalysis；
- execution steps；
- supervisor / pass_gate / scorecard，在运行入口允许且实际执行时；
- LearnedPath ingest result；
- conversation events / history read model。

不允许：

- 用 Codex 自然语言判断替代 pass_gate 或 run evidence；
- 用失败 / 未验证 run 对用户宣称“学习成功”；
- 把 direct internal service import 或隐藏脚本结果当成产品 live evidence；
- 没有 run_id、event_id、history 或测试输出就声称 E2E / live validation 通过。

## 产品模型 / 范围 / 路线图对齐（Product Model / Scope / Roadmap Alignment）

- Product model 对齐：本包修复 L1 autonomous learning 和 M11.3 runtime chat 之间的
  交接，不新增 L4 或新内部 Agent。
- Scope boundary 对齐：不让 LLM 逐步控制浏览器；能力发现和动作执行仍由代码 /
  Playwright runtime 负责。
- Roadmap / milestone 对齐：放在 M11.3 post-closeout follow-up。它由 `wagent chat`
  用户体验暴露，但根因在 L1 autonomous exploration。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

- 旧 LearnedPath 保持可读；本包不自动删除既有 provisional path。
- 旧 conversation history 保持可读；新增字段必须有默认值或兼容展示。
- `wagent verify` / `verify-scenario` 不受父包影响。
- 子包实现不得破坏已有 explicit learn / replay / task planning happy path。

## 不变契约

本轮不改变：

- Product lifecycle stages：L1 / L2 / L3 不变。
- Internal Agent roles：不新增 Agent；Conversation Orchestrator 和 existing learning
  services 继续按当前边界工作。
- Public API contracts：父包不改；子包如新增字段必须向后兼容。
- Database schema：父包不改；子包如需要 migration 必须单独设计。
- Replay status semantics：不改变 M10 replay status。
- Reporter / recovery / abort boundaries：不进入 M12 recovery / retry / abort。

## 非目标

- 不实现任意网页全量自动操作库。
- 不实现指数级所有筛选组合。
- 不把 target fixture 细节写进产品 runtime 或 prompt。
- 不运行 live autonomous run。

## 未决问题

- 子包 1 实现时是否需要新增 DB batch table，或只通过 `strategy_json` / events 表达
  discovery batch；由子包 1 technical design 决策。
