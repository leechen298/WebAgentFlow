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

## 待确认问题

- 是否需要在 `LearnedPathCandidate` schema 中增加 `score` 字段，还是暂时
  只用 `match_reasons` / `warnings`。
- `drift_evidence_summary` / `negative_evidence_summary` 当前从哪里读取，
  是否先留空。
- keyword overlap 第一版是否只做简单 lowercase substring / token overlap。
- page_template match 是否使用 exact / contains / normalized path template。
- 是否需要支持 limit / top_k 默认值为 10。
