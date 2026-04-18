# Scope Boundaries —— 明确不做的事

本文列出**当前阶段刻意不做**的能力。提出或实现这些之前，先来这里看一眼。清单上的项目都在等某个前置阶段完成后才会解锁。

## 当前阶段

**Phase 9** —— exploration loop + success evaluation + autonomous workbench。Phases 1–7 已完成（详见 [`architecture.zh.md`](./architecture.zh.md)）。

## 不在范围内

### 执行与编排

- **CLI 工具**（`apps/cli`）—— 等 exploration loop 在真实场景下验证后再做。
- **Skill 注册表 / Skill 运行时** —— 当前的 services 本身就是可调用接口，暂不做独立注册表。
- **Replay 执行策略** —— 跨环境确定性重放录制步骤是后续阶段的事。

### 监督

- **实时逐步 LLM 监督（Layer 1）** —— 先把事后评估（Layer 2）做稳，再考虑逐步监督，后者代价更高。
- **外部 AI 编码 Agent 监督** —— AI 编码工具（Claude Code、Codex 等）不得充当监督者。详见 `CLAUDE.zh.md` §"AI 编码 Agent —— 执行边界"。

### 学习与抽象

- **用户行为 ↔ 页面变化因果建模** —— Phase 10 范畴。
- **历史路径模板缓存** —— Phase 10 / 11。
- **用户纠正 & 行为教学** —— Phase 11。

### Parser / AST

- **"页面总结器"型把 DOM 重组为可读性版本的方案** —— AST 层必须保留结构保真度。如需摘要，是独立的下游视图。
- **带语义重构的 Simplified AST** —— Simplified AST 是结构保留的投影，不是改写。

### 数据 / 持久化

- **Approve / reject 完整落库**（autonomous 与 task-driven 都一样）—— 目前是 MVP 占位符，把 LearnedPath 的权威写回延后。
- **Autonomous-run 结果落库** —— 已交付。每次 autonomous run 都写入
  `exploration_runs`，`strategy_json.kind == "autonomous"`。列表 / 详情通过
  `GET /exploration/autonomous-runs/list|get`，支持按 `spec_id` / `scenario`
  过滤。仍然在范围外：approve 时的 LearnedPath 权威写回。
- **跨设备 / 云同步任务定义** —— 数据归用户所有，当前立场是本地优先。

## 何时回头看本清单

以下情况触发重评：

- 某阶段完成后问"下一步做什么？" —— 查清单里那些延后项的前置条件是否满足。
- 用户提的某个功能"看起来显而易见却不在代码里" —— 大概率是在这里被刻意延后了。
- 正在做的功能需要用到清单里某项 —— 考虑是否有更小的替代能解锁当前阶段，而不用把延后的东西拉进来。

## 相关文档

- [`architecture.zh.md`](./architecture.zh.md) §E —— 开发时间线。
- [`roadmap.zh.md`](./roadmap.zh.md) —— 运营里程碑。
- [`../CLAUDE.zh.md`](../CLAUDE.zh.md) —— 会话级别的 AI 编码 Agent 指引。

---

本文为 [`scope-boundaries.md`](./scope-boundaries.md) 的中文镜像，内容以英文版为准。
