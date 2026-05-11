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

Public 11.1.1 schema 仍优先输出 `LearnedPathCandidate`；score 可以暂存在
`match_reasons`，或在后续包明确扩展。

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

本包不读 raw HTML。
本包不调用 page analyzer。
本包不调用 autonomous run。

## Candidate filtering policy

第一版 policy：

- 默认 exclude `trust=deprecated`。
- Include confirmed / provisional / flaky。
- If `target_page_hint` exists, prefer page_template approximate match。
- If `scenario_hint` exists, prefer exact scenario match first。
- If no hint exists, fallback to task text keyword overlap with scenario /
  page_template。
- Do not require full semantic NLP。
- Do not use LLM embeddings in 11.1.2。
- No vector DB。
- No external search。

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
- match_reasons populated。
- warnings populated for flaky / drift / negative evidence。
- no LLM imports。
- no replay imports。
- no autonomous imports。
- no mutation of LearnedPath trust / hit_count。
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
