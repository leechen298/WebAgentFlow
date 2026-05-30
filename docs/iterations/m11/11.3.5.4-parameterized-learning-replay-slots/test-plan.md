# 测试计划（Test Plan）

状态：ready_for_implementation（design review passed，未开始实现）

## 测试边界

本包验证参数化 learning / replay 机制，不验证页面 DOM evidence 和 Reporter outcome。

允许运行：

- Python unit / integration tests。
- schema tests。
- mocked replay handler tests。
- targeted replay service tests。
- `git diff --check` / ruff 等静态检查。

不允许运行或声称：

- `verify-scenario`。
- autonomous run。
- product UI live run。
- `/records` DOM evidence verified。
- TaskResultReporter verified。
- 完整 `wagent chat` P0 closed loop。

## 测试矩阵

### Intake

| ID | Case | Input | Expected |
|---|---|---|---|
| ITK-1 | learn item name | `学习新增项目，名称叫测试项目A` | `intent=learn_operation`，slot `record_name=测试项目A` |
| ITK-2 | execute item name | `帮我新增项目，名称叫测试项目B` | `intent=execute_operation`，slot `record_name=测试项目B` |
| ITK-3 | alias 项目名 | `项目名是测试项目A` | slot 归一到 `record_name` |
| ITK-4 | alias name | `name 是测试项目A` | slot 归一到 `record_name` |

Target:

```text
apps/api/tests/test_conversation_intake.py
```

### Runtime fill values

| ID | Case | Expected |
|---|---|---|
| RTV-1 | intake slots include `record_name` | `_fill_values_from_intake()` 输出 `{"record_name": "测试项目A"}` |
| RTV-2 | username / password regression | 现有 credential fill values 行为不破坏 |
| RTV-3 | sensitive trace | `record_name` 非敏感可保留；password 不明文进 trace |

Target:

```text
apps/api/tests/test_conversation_chat_runtime.py
```

### LearnedPath parameterization

| ID | Case | Expected |
|---|---|---|
| LRN-1 | fill action value 等于 `fill_values.record_name` | action JSON 写入 `value_slot=record_name` |
| LRN-2 | 无匹配 fill action | binding report `not_bound`，不标成完整可参数化 |
| LRN-3 | 多个匹配 fill action | P0 可全部绑定并记录 warning |
| LRN-4 | dedup existing path | 只做 metadata-only merge，不覆盖不匹配 actions |

Targets:

```text
apps/api/tests/test_learning_run_service.py
apps/api/tests/test_learned_paths_repo.py  # 仅当实现新增 repo helper
```

### Replay schema / build

| ID | Case | Expected |
|---|---|---|
| RSC-1 | `ReplayRequest(url=...)` | `slot_overrides == {}` |
| RSC-2 | `ReplayRequest(..., slot_overrides={"record_name": "测试项目B"})` | schema 接受 |
| RSC-3 | raw action has `value_slot` | `_build_replay_actions()` 生成 `ReplayAction.value_slot` |

Target:

```text
apps/api/tests/test_learned_path_replay.py
```

### Replay effective action

| ID | Case | Expected |
|---|---|---|
| RPL-1 | action A + override B | `execute_action()` 收到 `value=测试项目B` |
| RPL-2 | action A + override B | `wait_for_change_after_action()` 收到 `value=测试项目B` |
| RPL-3 | override applied | step log 有 `value_slot=record_name`、`override_applied=true`、`effective_value=测试项目B` |
| RPL-4 | action has `value_slot` but override missing | replay failed / blocked-equivalent，不使用 A |
| RPL-5 | action has no `value_slot` | 不替换，保持旧 replay 行为 |

Target:

```text
apps/api/tests/test_learned_path_replay.py
```

### Chat runtime propagation

| ID | Case | Expected |
|---|---|---|
| CRT-1 | execute intake has `record_name=测试项目B` and path supports `value_slot=record_name` | mocked replay handler 收到 `slot_overrides.record_name=测试项目B` |
| CRT-2 | path lacks `value_slot=record_name` | runtime 阻断，不调用 replay handler |
| CRT-3 | no matched learned action | 保持原有 no-path 行为 |
| CRT-4 | Router recommended skill 不含 internal adapter | runtime 不接受 Router 推荐 internal adapter |

Targets:

```text
apps/api/tests/test_conversation_chat_runtime.py
apps/api/tests/test_conversation_replay_hook.py
```

## 建议命令

### Targeted tests

```bash
cd apps/api
../../.venv/bin/pytest \
  tests/test_conversation_intake.py \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_replay_hook.py \
  tests/test_learning_run_service.py \
  tests/test_learned_path_replay.py
```

### Static checks

```bash
git diff --check
```

如本包引入 ruff 影响范围，补跑：

```bash
uv run ruff check apps/api/app apps/api/tests
```

## Review 记录要求

实现完成后，`review.md` 必须记录：

- 实际修改文件。
- targeted tests 命令、exit code 和 pass / fail 数。
- 是否跑了 ruff / diff check。
- replay step log 或测试断言证明 effective value 是 `测试项目B`。
- 未运行项，包括 ExecutionEvidence、Reporter、TaskPathPlanner、live run。

## 不通过条件

以下任一情况不得标记本包完成：

- 只能证明 schema 支持 `slot_overrides`，但 chat runtime 没有传到 replay。
- replay 实际仍填入学习阶段的 `测试项目A`。
- `execute_action()` 使用 B，但 `wait_for_change_after_action()` 仍使用原始 action A。
- path 无 `value_slot=record_name` 时仍执行固定值 replay。
- 把 internal adapter 暴露成 Router 可推荐 skill。
- 把 DOM evidence / Reporter 结果误写成本包通过证据。
