# 11.2.3 实施计划

状态：代码实现计划已准备，待执行

本文档是 11.2.3 代码实现计划。实现阶段应按 `contract.md`、
`technical-design.md` 和 `test-plan.md` 修改 schema、learning service、replay
integration 和 scoped tests。

## 目标

代码实现的目标是把 11.2.2 已有的 step-level `wait_result` 聚合为
replay-level observation summary。

实现后，replay result 应能回答：

- replay 中有多少 step 带 `wait_result`？
- observed / timeout / skipped / not_required 各有多少？
- 是否观察到 primary signal？
- 是否只观察到 supporting signal？
- 是否存在需要 reporter 保守表达的不确定性？

## Planned files

计划修改：

- `apps/api/app/schemas/learned_path_replay.py`
- `apps/api/app/services/learning/learned_path_replay.py`
- `apps/api/tests/test_learned_path_replay.py`
- `apps/api/tests/test_replay_observation_summary.py`

计划新增：

- `apps/api/app/services/learning/replay_observation.py`

实现阶段可以创建上述源码或测试文件。

## Planned implementation direction

实现方向：

1. 从 `ReplayResult.steps` 读取每个 step 的 `wait_result`。
2. 统计 `observed` / `timeout` / `skipped` / `not_required`。
3. 聚合 primary / supporting signal kinds。
4. 生成 replay-level observation summary。
5. 把 summary 作为 `ReplayResult` 的可选字段暴露，保持向后兼容。
6. 不改变 `ReplayResult.status`。
7. 不调用 Task Result Reporter。
8. 不做 recovery / retry / abort。

## Planned tests

测试应覆盖：

- replay result can carry optional observation_summary。
- summary counts observed / timeout / skipped / not_required steps。
- summary identifies primary vs supporting signals。
- `network_idle_observed` only produces supporting evidence。
- timeout does not change replay status。
- no wait_result remains backward compatible。
- precheck blocked / drifted without action execution returns no
  `observation_summary`。
- observational path `actions=[]` returns `status=not_applicable` summary。
- reporter is not called。

## Technical Design and Test Plan

- `technical-design.md` 是代码实现的详细技术设计。
- `test-plan.md` 是代码实现完成后的详细验证计划。
- 代码实现必须遵循 `contract.md`、`technical-design.md` 和 `test-plan.md`。
- 本文档保留为实现计划和入口索引；更细执行依据以 `technical-design.md` 为准。

## 与 11.2.2 的关系

11.2.2 已经实现最小 step-level wait result：

- `url_changed` 和 `title_changed` 是当前实际 primary / target signals。
- `network_idle_observed` 只能作为 supporting signal。
- `page_load_finished` 保留在 schema 中，当前 MVP 不实际生成。

11.2.3 不扩大 11.2.2 signal 范围，不新增 wait strategy，不实现 page-load waiting。

## 与 11.2.5 的关系

11.2.3 只准备 replay-level observation evidence。11.2.5 才让 Task Result Reporter
消费这些 evidence 并生成保守任务结果汇报。

11.2.3 不调用 Reporter，不引入 Agent 式业务判断。

## 验证

代码实现完成后运行：

```bash
git diff --check

cd apps/api && ../../.venv/bin/python -m pytest \
  tests/test_replay_observation_summary.py \
  tests/test_learned_path_replay.py \
  -v

cd apps/api && ../../.venv/bin/ruff check \
  app/schemas/learned_path_replay.py \
  app/services/learning/replay_observation.py \
  app/services/learning/learned_path_replay.py \
  tests/test_replay_observation_summary.py \
  tests/test_learned_path_replay.py

cd apps/api && ../../.venv/bin/python -m pytest -q

find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

预期：

- `git diff --check` clean。
- scoped replay observation tests pass。
- ruff pass。
- full API suite pass；如果因 sandbox Playwright 权限失败，必须记录失败原因，不能写成
  PASS。
- forbidden directory check 无输出。

## 完成措辞

使用：

```text
11.2.3 replay observation aggregation implemented.
```

不要写：

- `Task Result Reporter integration complete`。
- `runtime observation fully implemented`。
- `M12 started`。
