# Scope Boundaries —— 明确不做的事

本文列出**当前交付里程碑刻意不做**的能力。提出或实现这些之前，先来这里看一眼。清单上的项目都在等某个前置里程碑完成后才会解锁。

**产品"要做什么"**（L1/L2/L3 生命周期模型和各个 Agent）见
[`product-model.zh.md`](./product-model.zh.md)。如果一个提议在那份
文档里没位置、本清单也没列为"不做"，**停下来问**，不要擅自发明。

## 当前交付里程碑

**M10 —— Path Asset Foundation / 路径资产基础**。历史迭代目录仍沿用
`phase-10`，但新规划语言使用 M10，避免和生命周期阶段 L1/L2/L3 混淆。

当前可执行包：`10.2-replay-execution-drift-detection`。
M10.2 只实现 LearnedPath replay 和 drift detection：

- 从 catalog 消费一条已有 LearnedPath
- 针对用户提供的 URL 回放已存 actions
- 返回 replay status、step logs，以及 page mismatch、signature changed、
  `target_missing`、`unsupported_action` 等 drift reasons

M10.2 不是 L3 task runner。Replay / drift 结果未来可以成为 failure
evidence 和 drift evidence 的来源，但本包不要求实现完整的 negative
knowledge store。

## 不在范围内

### 执行与编排

- **Runtime conversation CLI / 运行时沟通 CLI** —— 不属于 M10.2。这里要区分
  三类 CLI：
  - 当前 `wagent verify` / `verify-scenario`：已经存在的开发验证 skill
    后端，用于可审计的 scenario check；
  - M11.0 Runtime Conversation CLI：未来 WebAgentFlow 运行时产品入口，用户
    在这里和 WebAgentFlow 沟通；
  - M16 External CLI：后续面向外部调度、本地脚本和集成的稳定工具接口。
  M10.2 期间只有现有 `verify-scenario` 后端存在；M11.0 和 M16 的 CLI
  都不属于本包。
- **Skill / Tool 接口（给第三方 Agent）** —— 对外接口仍然是 HTTP API。
  唯一例外是 `verify-scenario` Claude Code skill（由 `wagent` CLI 通过
  `wagent skill install` 生成到 `~/.claude/skills/`），包装同一个 HTTP
  端点并带上可审计的汇报契约，让 AI 编码 Agent 可以跑 scenario 而不
  绕过项目内 Supervisor Agent。更广义的第三方 Agent 注册表属于后续
  里程碑。
- **Task-to-Path Planning MVP** —— 用户任务 / chat 入口、Agent D Path
  Planner、路径检索 / 排序、slot binding、执行前确认、task result
  verification、Agent E 结果汇报属于 M11.1，不属于 M10.2。
- **Recovery / abort 对话** —— Agent F Recovery Dialogue 和 Agent G
  Abort Dialogue 属于 M12，不属于 M10.2。
- **Agent H Teaching Guide Agent / 教学引导 Agent** —— guided teaching 属于
  M13，不属于 M10.2。
- **Runtime Agent orchestration / 运行时 Agent 编排** —— M10.2 不实现 Agent
  D / E / F / G / H，不实现 session controller，不实现暂停 / 继续 /
  abort 命令，不实现 takeover 路由，也不实现面向用户的运行时对话。
- **Multi-page workflow composition / 多页面工作流编排** —— 多个 LearnedPath
  组成跨页面 workflow 属于 M17，不属于 M10.2。
- **Action risk & consent gate / 操作风险与确认门** —— 风险分类、
  destructive action 拦截、用户自定义 risk policy、执行前 consent gate
  属于 M11 / M12 后续工作，不属于 M10.2。

### 监督

- **L3 实时逐步 LLM 监督** —— 大模型只能在规划、报告、恢复 / 中断
  对话或用户教学 / 接管边界处介入，不能在 L3 执行过程中逐步决定浏览器动作。
- **外部 AI 编码 Agent 监督** —— AI 编码工具（Claude Code、Codex 等）不得充当监督者。详见 `CLAUDE.zh.md` §"AI 编码 Agent —— 执行边界"。

### 学习与抽象

- **用户引导学习与纠正** —— 可视化浏览器接管、真实用户动作记录、
  provenance 写回、路径纠正属于 M13。
- **Guided teaching / 引导式教学模式** —— guided teaching、元素
  highlight、indicator / tooltip overlay，以及 Teaching Guide Agent 交互
  属于 M13。M10.2 不做 visible browser teaching overlay，也不记录用户
  真实操作。
- **控件覆盖扩展与模式归纳** —— popup 控件、自定义 click-toggle
  控件、更多 label handler、跨页面 pattern mining 属于 M14，除非明确
  重新排优先级。
- **Learning Reporter 产品表面** —— Agent C 的用户可读学习报告属于
  M14。当前 workbench / history 输出是开发者取证面，不是 Agent C 的
  最终报告。
- **Negative knowledge store / 负面知识资产化** —— failed attempts、
  replay drift、`target_missing`、`unsupported_action` 和 user corrections
  的正式资产化属于 M14 / M15。M10.2 可以产出 replay / drift evidence，
  但不实现完整 store。

### Parser / AST

- **"页面总结器"型把 DOM 重组为可读性版本的方案** —— AST 层必须保留结构保真度。如需摘要，是独立的下游视图。
- **带语义重构的 Simplified AST** —— Simplified AST 是结构保留的投影，不是改写。

### 数据 / 持久化

- **完整对外接口套件** —— 面向外部调度者的稳定 API / CLI / Skill /
  Tool 属于 M16。
- **目标站点权限 / session 边界** —— 默认假设 WebAgentFlow 操作者已经拥有
  操作目标网页的权限。cookies、`localStorage`、session state 和目标站点
  权限由操作者和目标网页负责。session 失效、权限不足、目标站点认证页
  回退、操作失败，属于 runtime failure / recovery 问题。
- **Artifact lifecycle / Artifact 生命周期** —— download / export /
  upload / screenshot artifact 的 capture、storage、display / return、
  retention、cleanup 属于后续 M11 / M15 / M16 / M18 工作。M10.2 只返回
  replay result 和可审计状态。
- **Engine data hygiene / 引擎数据卫生** —— logs、screenshots、artifacts、
  conversation records、LLM prompt payloads 的 retention、cleanup、
  redaction、audit policy 属于后续 hygiene 工作，不属于 M10.2。
- **Autonomous-run 结果落库** —— 已交付。每次 autonomous run 都写入
  `exploration_runs`，`strategy_json.kind == "autonomous"`。列表 / 详情通过
  `GET /exploration/autonomous-runs[/{run_id}]`，支持按 `spec_id` / `scenario`
  过滤。
- **LearnedPath 写回** —— M10.1 已为 `pass_gate = pass` autonomous run
  交付。来自用户引导学习的进一步写回属于 M13。
## 何时回头看本清单

以下情况触发重评：

- 某里程碑完成后问"下一步做什么？" —— 查清单里那些延后项的前置条件是否满足。
- 用户提的某个功能"看起来显而易见却不在代码里" —— 大概率是在这里被刻意延后了。
- 正在做的功能需要用到清单里某项 —— 考虑是否有更小的替代能解锁当前里程碑，而不用把延后的东西拉进来。

## 相关文档

- [`architecture.zh.md`](./architecture.zh.md) §E —— 开发时间线。
- [`roadmap.zh.md`](./roadmap.zh.md) —— 运营里程碑。
- [`../CLAUDE.zh.md`](../CLAUDE.zh.md) —— 会话级别的 AI 编码 Agent 指引。

---

本文为 [`scope-boundaries.md`](./scope-boundaries.md) 的中文镜像，内容以英文版为准。
