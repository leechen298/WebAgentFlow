# 11.3.12 Code Review Handoff

日期：2026-06-06

## Review Scope

本文件整理对 `/goal 开发 11.3.12-bounded-learning-composable-capability-assets`
当前工作区的只读代码审查结果，供后续聊天接手修复。

审查背景：

- 本包曾中断并在另一个聊天接力完成。
- 父包 `CURRENT_STATE.md`、父包 `review.md`、M11 索引已被更新为
  `PACKAGE_COMPLETE`。
- 当前工作区仍包含大量 11.3.10 / 11.3.11 / 11.3.12 未提交和未跟踪文件。
- 本次审查未修改代码，未 stage / commit，未运行 live autonomous validation，
  未运行 `verify-scenario`，未运行 `wagent chat` live run。

审查方式：

- 主线程读取当前工作区关键文档和源码。
- 使用 3 个只读 subagents 分别审查：
  - 父/子包文档与 evidence consistency；
  - 11.3.12.1 / 11.3.12.2 model / repo / migration / batch lifecycle；
  - 11.3.12.3 / 11.3.12.4 capability hints / composition runtime。

## Overall Verdict

当前不建议把 11.3.12 视为“干净可交接的 PACKAGE_COMPLETE”。

原因不是 live validation 未运行，而是：

- 存在会影响 11.3.12.2 batch lifecycle 的真实代码缺陷；
- 11.3.12.4 `CapabilityComposer` 和合同之间有 P1 级语义偏差；
- 子包 closeout 元数据仍有中断接力残留，会让 `/goal` 恢复路由看到冲突信号。

## Resolution Update - 2026-06-06

本文件中的 P1 / P2 / P3 findings 已在当前工作区复核并处理：

- P1 batch 异常路径：已修复。`LearningRunService` 在 batch 创建后遇到
  seed analysis、scenario planning、scenario explorer 或 `_persist_finished_run()`
  异常时，会 terminal close batch，并返回 `learning_batch_id` /
  `learning_batch_status` / `learning_batch_summary`。
- P1 Composer page-scope：已修复。`CapabilityCompositionRequest` 增加
  `query_signature`；candidate 和 preferred LearnedPath 均按 page template +
  query signature + DOM fingerprint fail-closed。
- P1 Composer operation 支持集：已修复。composer 现在区分 ingest adapter 与
  executable operation，并将 `input` / `text` / `date` / `month` 映射到
  `set_value`，将 `toggle` 映射到 `click`。
- P1 子包状态冲突：已修复。11.3.12.1 / 11.3.12.3 / 11.3.12.4 入口 review
  状态已同步为 `PACKAGE_COMPLETE`。
- P2 cancel、public/private serialization、planned scenario redaction、combobox
  support semantics：已修复并补测试。
- P3 repository pagination：已修复，cursor / `limit + 1` 已下推到 SQL。
- P3 untracked whitespace 风险：已用 explicit scoped `rg '[[:blank:]]+$'`
  覆盖相关 tracked / untracked files。

当前验证：

- `PYTHONPATH=. ../../.venv/bin/pytest tests/test_capability_composer.py
  tests/test_learning_run_service.py tests/test_learning_batches_repo.py
  tests/test_bounded_learning_batch_lifecycle.py tests/test_filter_capability_discovery.py
  tests/test_capability_hints.py tests/test_learned_capabilities_repo.py
  tests/test_learned_paths_repo.py tests/test_learned_path_replay.py -q`：
  164 passed。
- scoped `uv run ruff check ...`：All checks passed。
- hardcoding scan：仅既有 generic `data-testid` 采集 / 脱敏命中；无 `/users`、
  Alice/Bob、validation-site 或用户管理样例进入 runtime。

## P1 Findings

### P1. Batch 异常路径会留下非终态 LearningBatch

文件：

- `apps/api/app/services/learning/learning_run_service.py`

关键位置：

- `_run_capability_discovery()` 创建并提交 `pending` batch：
  `learning_run_service.py:267`
- seed analysis / scenario explorer / `_persist_finished_run()` 正常路径外抛异常时，
  外层 `run()` catch 返回普通 failed result：
  `learning_run_service.py:181`
- 真正 terminal close 只在正常循环后发生：
  `learning_run_service.py:458`

影响：

- DB 里可能长期保留 `pending` / `running` batch。
- 返回给 conversation 层的 failed result 不含 `learning_batch_id` /
  `learning_batch_status` / `learning_batch_summary`。
- `chat_runtime.py:3152` 只能记录无 batch 的失败，破坏 11.3.12.2
  “同步 v1 必须返回 closed terminal status + batch id”的合同。

建议修复：

- 在 `_run_capability_discovery()` 内部包住 batch 创建后的阶段。
- 一旦 batch 已创建，任何异常都应尝试 close 为 terminal `failed`，
  summary 记录异常阶段和 redacted error。
- 返回的 `LearningRunResult` 必须带 `learning_batch_id`、terminal status、
  summary。
- 增加测试：seed analysis 抛异常、scenario explorer 抛异常、
  `_persist_finished_run()` 抛异常时 batch 均 terminal close。

### P1. CapabilityComposer page-scope fail-closed 不完整

文件：

- `apps/api/app/services/learning/capability_composer.py`
- `apps/api/app/schemas/capability_composition.py`
- `docs/iterations/m11/11.3.12.4-capability-composition-runtime/contract.md`

关键位置：

- candidate 只校验 `page_template`，DOM 只在 request 带
  `dom_fingerprint` 时校验：`capability_composer.py:160`
- preferred LearnedPath 缺少 DOM 时可仅凭 confirmed + page_template 命中：
  `capability_composer.py:242`
- 12.4 contract 要求 page template + query signature + DOM fingerprint /
  current hints compatible：`contract.md:37`

影响：

- 同一个 page template 下不同 query shape / DOM 的旧 capability 可能进入
  composition。
- unknown-page / drifted-page 场景可能错误优先复用 confirmed LearnedPath。
- 这会削弱 11.3.12 的 target-agnostic 和 evidence-isolation 边界。

建议修复：

- 在 `CapabilityCompositionRequest` 中加入 `query_signature`，并在候选检查中
  与 capability/path 的 `query_signature` 做兼容校验。
- 若 policy `require_dom_fingerprint_match=True`，request 缺少当前 DOM
  fingerprint 时应 fail closed，不能跳过 DOM 校验。
- preferred LearnedPath 也必须经过同样 page scope 校验。
- 如当前 hints 可用，增加 control / region / terminal ref 兼容检查或明确
  标为 unsupported，而不是 silent ready。

### P1. CapabilityComposer 没有按执行器支持集校验 operation

文件：

- `apps/api/app/services/learning/capability_composer.py`
- `apps/api/app/services/learning/learned_path_replay.py`
- `apps/api/tests/test_capability_composer.py`

关键位置：

- composer 只白名单 `adapter_type`：`capability_composer.py:175`
- public `action_kind` 使用 `action_schema_json.operation`：
  `capability_composer.py:307`
- replay 支持集为 `fill/set_value/select/select_first_option/click/press/observe`：
  `learned_path_replay.py:38`
- 当前测试把 `operation=input/text/date/month` 的候选断言为 `ready`：
  `test_capability_composer.py:237`

影响：

- 可能生成 `status=ready`，但 private handoff 的 operation 无法由
  replay / executor 执行。
- 这是 fail-open，不应进入 `ready` plan。

建议修复：

- 增加 `supported_operations` 或直接复用 replay 支持集。
- `_candidate_rejection_reason()` 同时校验 `operation` 和 `adapter_type`。
- 对 ingest adapter 名称和 executable operation 做明确映射：
  `input/text/date/month -> set_value` 或 `fill`，但不能把这些值原样作为
  executable operation。
- 更新测试：`input/text/date/month` 不应作为 operation 进入 ready；若作为
  adapter type，应映射到可执行 operation。

### P1. 11.3.12.1 子包入口仍会把 agent 路由回待实现

文件：

- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/README.md`
- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/review.md`
- `docs/iterations/m11/11.3.12-bounded-learning-composable-capability-assets/CURRENT_STATE.md`

关键位置：

- 父包 `CURRENT_STATE.md` 标记 11.3.12.1 `PACKAGE_COMPLETE`。
- 11.3.12.1 `README.md:3` 仍是 `ready_for_implementation`。
- 11.3.12.1 `README.md:58` 仍写“下一步只允许实现本包”。
- 11.3.12.1 `review.md:3` 顶部仍是 `in_progress`。
- 11.3.12.1 `review.md:10` next_action 仍是路由到 11.3.12.2 planning。

影响：

- 违反父包 `GOAL_RUNNER.md` 的状态冲突 hard stop 规则。
- 后续 `/goal` 恢复时会看到父包 complete、子包待实现/下一包路由并存。
- 不能声称所有 routing surfaces 已同步。

建议修复：

- 同步 11.3.12.1 `README.md` 顶部状态、当前状态说明。
- 同步 11.3.12.1 `review.md` 顶部状态和 `next_action`。
- 复查 11.3.12.2 / 11.3.12.3 / 11.3.12.4 review 顶部状态和 route 字段。

## P2 Findings

### P2. repository cancel 语义不可靠

文件：

- `apps/api/app/repos/learning_batches_repo.py`
- `apps/api/app/services/learning/learning_batch_controller.py`
- `apps/api/app/core/db.py`

问题：

- `request_cancel()` 写入 `cancel_requested`。
- `LearningBatchController.boundary_state()` 只是 `repo.get()` 当前 session
  对象。
- 项目 Session `expire_on_commit=False`，外部 session 的 cancel 不一定刷新到
  当前 service session。
- 若 cancel 发生在 seed analysis 后、`mark_running()` 前，`mark_running()`
  可能直接覆盖为 `running`。

建议：

- boundary check 使用 refresh / populate_existing / 独立 query 读取最新状态。
- `mark_running()` 前再次检查 terminal/cancel_requested，避免覆盖 cancel。
- 增加跨 session cancel 测试。

### P2. CapabilityCompositionResult 默认可序列化 private handoff

文件：

- `apps/api/app/schemas/capability_composition.py`

问题：

- `CapabilityCompositionResult` 包含 `execution_handoff`。
- `CapabilityExecutionHandoff` 内含 `ordered_action_schemas`，可包含 selector /
  control binding 等 private payload。
- 当前没有 router 直接暴露 composer，但未来接 API / Conversation 时容易误返回。

建议：

- 拆分 public result 和 service-internal result。
- 或给 public dump / response model 强制 exclude `execution_handoff`。
- 增加测试：public serialization 不包含 private handoff。

### P2. LearningBatchDetail planned_scenarios redaction 不覆盖样本值

文件：

- `apps/api/app/schemas/learning_batch.py`
- `apps/api/app/services/learning/capability_discovery.py`
- `apps/api/app/services/learning/learning_run_service.py`

问题：

- planned scenario payload 包含 `input_bindings`、`fill_values`、
  `toggle_values`。
- discovery binding 明确含 `"value"`。
- `LearningBatchDetail` 会投影 `planned_scenarios`，但 redaction tokens 未覆盖
  `fill_values`、`toggle_values` 或 binding 内普通 `"value"`。

建议：

- 对 planned scenarios 做结构化 redaction，而不是仅按 key token。
- 保留 capability id / adapter / binding key，删除 sample values。
- 增加 schema projection 测试。

### P2. hint/discovery 对 combobox 的 supported 语义与 ingest 不一致

文件：

- `apps/api/app/services/learning/capability_hints.py`
- `apps/api/app/services/learning/capability_discovery.py`
- `apps/api/app/services/learning/learning_run_service.py`

问题：

- hint builder 给 combobox `adapter_type="combobox"`。
- discovery 只要 adapter 不是 `unsupported` 就标 supported。
- `_capability_kind_for_binding()` 不接受 `combobox`。
- 结果是 supported scenario 可能执行后无法入库，fail-closed 发生太晚。

建议：

- 要么将 combobox 标为 unsupported，直到 ingest / executor 全链路支持；
- 要么将 combobox 映射到 `select_first_option` 或明确的 executable adapter，
  并补端到端单元测试。

### P2. 11.3.12.1 static-check gate 未按 test-plan 字面满足

文件：

- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/test-plan.md`
- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/review.md`

问题：

- test-plan 要求 `uv run ruff check apps/api/app apps/api/tests`。
- review 记录 whole API ruff exit 1，原因是 existing unrelated lint failures。
- scoped ruff pass 有价值，但不等于 whole API gate pass。

建议：

- 更新 gate 语义为 scoped gate，并明确 whole API ruff 是 known unrelated fail；
- 或保留 gate unmet/caveated，不把它写成 clean closeout。

## P3 Findings

### P3. repo 分页没有下推 cursor / limit 到数据库

文件：

- `apps/api/app/repos/learned_capabilities_repo.py`
- `apps/api/app/repos/learning_batches_repo.py`

问题：

- `list_page()` 和 `list_for_session()` 都先 `.all()` 全量取回，再 Python 侧
  cursor 过滤和切窗。
- 小数据测试可以通过，但数据增长后会有内存和延迟问题，索引无法保护 keyset
  pagination。

建议：

- 将 cursor 条件转换为 SQLAlchemy where 条件。
- 使用 `limit + 1` 下推到 DB。

### P3. 父包 git scope evidence 低估未跟踪范围

文件：

- `docs/iterations/m11/11.3.12-bounded-learning-composable-capability-assets/review.md`

问题：

- 父包 review 记录 `git diff --check` pass。
- 但 `git diff --check` 不覆盖 untracked 文件。
- 当前 11.3.12 多个目录仍是 untracked。

建议：

- 提交前用 `git add -N` 或 staging 后重跑 whitespace / scope checks。
- 明确检查 untracked child package docs。

## Not Reproduced / Not Run

本次 code review 没有运行：

- pytest；
- ruff；
- Alembic online migration；
- live autonomous validation；
- `verify-scenario`；
- `wagent chat` live run。

之前 closeout 文档声称的测试结果未在本次审查中重新执行，只作为已有记录审阅。

## Suggested Next Fix Order

1. 修复 `LearningRunService` batch 异常 closeout，并补异常路径测试。
2. 修复 `CapabilityComposer` page-scope / operation fail-closed，并更新测试。
3. 修复 11.3.12.1 / 11.3.12.2 / 11.3.12.3 / 11.3.12.4 review / README
   closeout 元数据冲突。
4. 修复 private handoff / batch detail redaction 的未来 API 风险。
5. 修复 cancel 跨 session 语义和 repository pagination。
6. staging 前重跑 scoped whitespace / status / ruff / pytest；如果要声明 broad gate，
   必须跑 broad gate 或把 caveat 写清楚。

## Handoff Note

后续聊天接手时不要直接从父包 `PACKAGE_COMPLETE` 继续 commit。应先按以上 P1
修复并更新子包 review / parent CURRENT_STATE，再重新决定最终状态。
