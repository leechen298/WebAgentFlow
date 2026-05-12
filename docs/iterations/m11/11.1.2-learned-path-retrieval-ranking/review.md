# 审核与反思

## 规划初始化

- 本目录用于 11.1.2 LearnedPath Retrieval and Ranking。
- 前置 11.1.1 Task Planning Domain Contract 已完成。
- 本包建立了 deterministic retrieval / ranking 层，为后续 slot binding 和
  Task Path Planner 提供候选路径。

## 已决策（保持不变）

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
  `negative_evidence_summary` 默认留空。`drift_evidence_summary` 从已有
  LearnedPath `trust_reason` 保守填充；若 trust 为 confirmed 则不填充。
  本包没有新增负面知识表。
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

## 实际交付

- `apps/api/app/services/task_planning/retrieval.py`
  - `LearnedPathRetrievalService(repo).retrieve_candidates(task_intent, limit=10)`
  - 内部 `_RankedCandidate` 类型（不暴露 public score 字段）
  - `_tokenize()` 确定性 lowercase token 提取
- `apps/api/app/services/task_planning/__init__.py`
- `apps/api/app/repos/learned_paths_repo.py`
  - 新增只读 `list_candidates()` 返回所有 non-deprecated LearnedPaths
- `apps/api/tests/test_task_planning_retrieval.py`
  - 38 个测试：空目录、trust 过滤、trust 优先级、scenario/page 匹配、
    hit_count、keyword overlap、limit clamping、score 内部性、match_reasons /
    warnings、drift/negative evidence 保守策略、无副作用、contract rules、
    tokenizer 单元测试

## 验证记录

- `cd apps/api && ../../.venv/bin/pytest tests/test_task_planning_retrieval.py tests/test_task_planning_schemas.py -v`
  - 结果：`63 passed`
- `cd apps/api && ../../.venv/bin/ruff check app/services/task_planning/retrieval.py app/services/task_planning/__init__.py tests/test_task_planning_retrieval.py`
  - 结果：`All checks passed!`
- `cd apps/api && ../../.venv/bin/pytest -v` (full suite)
  - 结果：`918 passed, 65 skipped`
- `git diff --check`
  - 结果：clean

## 范围偏差与后续风险

- 无已知范围偏差。所有 hard boundary（不调用 LLM、不 replay、不 autonomous run、
  不读 raw HTML、不 slot binding、不生成 route plan）均已遵守。
- `drift_evidence_summary` 当前唯一来源是 `trust_reason`。当 LearnedPath 的
  trust 为 confirmed 时，即使有 trust_reason，也不填充 drift_evidence_summary
  （因为 confirmed 意味着当前认为没有漂移）。若后续需要更丰富的漂移信号，
  需要 M14/M15 的 replay evidence / negative knowledge store。
- `_tokenize()` 对 CJK 的处理依赖 Python `re` 的 Unicode `\w` 行为：CJK
  字符作为单个 token 保留（不被拆分）。这在当前 keyword overlap 场景下是
  可接受的，因为 "登录" 作为整体 token 与 "登录" 匹配即可。

## 待确认问题

- 后续是否需要 explicit score 字段（供 Task Path Planner 消费）。
- 后续是否接入正式 negative knowledge store。
- 后续是否加入 embedding / vector retrieval。
- 后续是否需要 API endpoint 暴露 retrieval preview。
