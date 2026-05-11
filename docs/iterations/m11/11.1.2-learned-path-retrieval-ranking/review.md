# 审核与反思

## 规划初始化

- 本目录用于 11.1.2 LearnedPath Retrieval and Ranking。
- 当前状态：intent / plan 初始化，尚未实现代码。
- 前置 11.1.1 Task Planning Domain Contract 已完成。
- 本包将建立 deterministic retrieval / ranking 层，为后续 slot binding 和
  Task Path Planner 提供候选路径。

## 已决策

- 11.1.2 是 deterministic retrieval / ranking service，不是 LLM Agent。
- 不调用 Task Path Planner。
- 不调用 LLM provider。
- 不执行 replay。
- 不调用 autonomous run。
- 不读取 raw HTML。
- 第一版不使用 embeddings / vector DB / external search。
- deprecated LearnedPath 默认排除。
- no candidates 时返回空列表，不自动学习。
- ranking score 必须可解释、可测试。
- 11.1.2 不修改 11.1.1 的 `LearnedPathCandidate` schema，不新增 public
  `score` 字段；ranking score 作为 service 内部实现细节。对外候选解释通过
  `match_reasons` 和 `warnings` 表达。如果未来 Task Path Planner 需要显式
  score，再在后续包单独扩展 schema。
- 11.1.2 第一版不实现正式 negative knowledge store；
  `negative_evidence_summary` 默认留空。`drift_evidence_summary` 可以从已有
  LearnedPath trust / replay evidence 可用字段中保守填充；如果当前没有稳定
  来源，则留空。本包不得为了填这些字段新增负面知识表。
- keyword overlap 第一版只做 deterministic lowercase token overlap。输入文本
  来自 `TaskIntent.raw_text`、`normalized_goal`、`scenario_hint`、
  `target_page_hint`；候选文本来自 `LearnedPath.scenario` 和
  `LearnedPath.page_template`。中文第一版采用 substring / simple contains，
  不引入分词器依赖。
- page_template match 第一版使用 normalized contains / exact-ish match：
  exact match gets strongest reason，contains match gets weaker reason。不调用
  page_signature analyzer，不读取 raw HTML，不重新分析页面。`target_page_hint`
  为空时，不因 page_template 不匹配直接排除候选。
- `limit` 默认 10，最小 1，最大 50；service layer clamps out-of-range values
  to `[1, 50]`，ranking 后返回 top `limit` candidates。
- `trust=deprecated` 默认排除。`trust=flaky` 可以进入候选，但必须添加
  warning，且 trust score 低于 confirmed / provisional。confirmed 优先级高于
  provisional，provisional 高于 flaky。hit_count 是正向信号，但不能让
  deprecated 进入候选，也不能压过 trust 的基本优先级。

## 待确认问题

- 后续是否需要 explicit score 字段。
- 后续是否接入正式 negative knowledge store。
- 后续是否加入 embedding / vector retrieval。
- 后续是否需要 API endpoint 暴露 retrieval preview。
