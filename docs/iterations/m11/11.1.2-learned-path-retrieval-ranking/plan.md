# 实施计划

## 触及的文件 / 模块

后续实现阶段可能触及：

- `apps/api/app/services/task_planning/retrieval.py` —— planned retrieval /
  ranking service。
- `apps/api/app/services/task_planning/__init__.py` —— export if needed。
- `apps/api/app/repos/learned_paths_repo.py` —— optional read-only query
  helper。
- `apps/api/app/schemas/task_planning.py` —— only if minor candidate field
  adjustment is truly needed；default should reuse 11.1.1 schema。
- `apps/api/tests/test_task_planning_retrieval.py`。
- `docs/iterations/m11/11.1.2-learned-path-retrieval-ranking/review.md`。

## Service contract

推荐函数 contract：

```text
retrieve_learned_path_candidates(
    task_intent: TaskIntent,
    *,
    limit: int = 10,
) -> list[LearnedPathCandidate]
```

或 class contract：

```text
LearnedPathRetrievalService(repo: LearnedPathRepository)

retrieve_candidates(task_intent: TaskIntent, limit: int = 10) -> list[LearnedPathCandidate]
```

如果需要返回 score debug，可规划内部类型：

```text
RankedLearnedPathCandidate
- candidate: LearnedPathCandidate
- score: float
- score_reasons: list[str]
```

11.1.2 不修改 11.1.1 的 `LearnedPathCandidate` schema，不新增 public
`score` 字段。Ranking score 是 service 内部实现细节；对外候选解释通过
`match_reasons` 和 `warnings` 表达。如果未来 Task Path Planner 需要显式
score，再在后续包单独扩展 schema。

`limit` policy：

- default: 10
- min: 1
- max: 50
- service layer clamps out-of-range values to `[1, 50]`
- ranking 后返回 top `limit` candidates

## Retrieval inputs

从 `TaskIntent` 使用：

- `raw_text`
- `normalized_goal`
- `target_page_hint`
- `scenario_hint`
- `required_outputs`
- `constraints`
- `uncertainty`

从 LearnedPath 使用：

- id
- scenario
- page_template
- trust
- hit_count
- actions count / action summary if already available
- drift evidence summary if available
- negative evidence summary if available

Evidence summary policy：

- 11.1.2 第一版不实现正式 negative knowledge store。
- `negative_evidence_summary` 第一版默认留空。
- `drift_evidence_summary` 第一版可以从已有 LearnedPath trust / replay
  evidence 可用字段中保守填充；如果当前没有稳定来源，则留空。
- 本包不得为了填这些字段新增负面知识表。
- 后续 M14 / M15 再正式资产化 failure evidence / negative knowledge。

本包不读 raw HTML。
本包不调用 page analyzer。
本包不调用 autonomous run。

## Candidate filtering policy

第一版 policy：

- 默认 exclude `trust=deprecated`。
- Include confirmed / provisional / flaky。
- `trust=flaky` 可以进入候选，但必须添加 warning，并且 trust score 低于
  confirmed / provisional。
- confirmed 优先级高于 provisional，provisional 高于 flaky。
- hit_count 是正向信号，但不能让 deprecated 进入候选，也不能压过 trust
  的基本优先级。
- If `target_page_hint` exists, prefer page_template normalized contains /
  exact-ish match。
- If `scenario_hint` exists, prefer exact scenario match first。
- If no hint exists, fallback to task text keyword overlap with scenario /
  page_template。
- If `target_page_hint` is empty, do not exclude a candidate only because its
  page_template does not match.
- Do not require full semantic NLP。
- Do not use LLM embeddings in 11.1.2。
- No vector DB。
- No external search。

Page template match strategy：

- exact match gets strongest reason。
- contains match gets weaker reason。
- matching is normalized enough for simple case / slash differences, but does
  not call page_signature analyzer。
- 不读取 raw HTML。
- 不重新分析页面。

Keyword overlap strategy：

- 第一版只做 deterministic lowercase token overlap。
- 输入文本来自 `TaskIntent.raw_text`、`TaskIntent.normalized_goal` if present、
  `TaskIntent.scenario_hint`、`TaskIntent.target_page_hint`。
- 候选文本来自 `LearnedPath.scenario`、`LearnedPath.page_template`。
- tokenization 使用简单规则：lowercase；按 non-alphanumeric / non-CJK
  boundary 拆分 where practical。
- 中文第一版采用 substring / simple contains，不引入分词器依赖。
- 不用 LLM、embedding、vector DB 或 external search。

## Ranking policy

使用 deterministic score。

建议 score components：

```text
+50 exact scenario_hint match
+30 page_template / target_page_hint match
+20 trust confirmed
+10 trust provisional
+0 trust flaky
-100 deprecated or excluded
+min(hit_count, 10)
+keyword overlap score from raw_text / normalized_goal against scenario/page_template
- drift warning penalty
- negative evidence penalty
```

要求：

- score formula 必须简单、可测试。
- ranking must be deterministic。
- reasons must be explainable through `match_reasons` and `warnings`。
- 不引入 LLM 或 embedding。

## Output policy

每个 `LearnedPathCandidate` 至少填充：

- `learned_path_id`
- `scenario`
- `page_template`
- `trust`
- `hit_count`
- `match_reasons`
- `warnings`
- `drift_evidence_summary` optional
- `negative_evidence_summary` optional

如果 no candidates：

- 返回空列表。
- 不自动调用 autonomous learning。
- 不 hidden relearn。
- 后续 Task Path Planner / Orchestrator 决定如何与用户沟通。

## Repo policy

如果 `LearnedPathRepository` 缺少查询能力，可新增 read-only helper：

```text
list_candidates(limit: int | None = None)
```

或按 scenario / page_template 查询的 helper。

要求：

- 只读。
- 不改变 trust。
- 不改变 hit_count。
- 不写入 LearnedPath。
- 不新增 user / account / tenant。

## Testing plan

后续实现阶段至少覆盖：

- returns empty list when no LearnedPath exists。
- retrieves confirmed / provisional / flaky candidates。
- excludes deprecated candidates by default。
- exact scenario_hint match ranks first。
- target_page_hint / page_template match contributes to score。
- confirmed outranks provisional when other signals equal。
- flaky is included but warning is added。
- hit_count contributes but does not allow deprecated to win。
- keyword overlap contributes deterministic score。
- limit defaults to 10 and clamps to min 1 / max 50。
- score remains internal and does not appear as a public
  `LearnedPathCandidate` field。
- match_reasons populated。
- warnings populated for flaky / drift / negative evidence。
- drift / negative summaries are conservative and may be empty when no stable
  source exists。
- no LLM imports。
- no replay imports。
- no autonomous imports。
- no mutation of LearnedPath trust / hit_count。
- no autonomous call when no candidates are found。
- no user / account / tenant fields。
- existing task planning schema tests still pass。

## 验证

后续实现阶段运行：

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_task_planning_retrieval.py \
  tests/test_task_planning_schemas.py -v

cd apps/api && ../../.venv/bin/ruff check \
  app/services/task_planning/retrieval.py \
  app/services/task_planning/__init__.py \
  tests/test_task_planning_retrieval.py

git diff --check
```

当前文档阶段只运行：

```bash
git diff --check
```
