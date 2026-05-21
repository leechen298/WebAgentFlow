# 契约（Contract）

状态：draft_docs（待评审，未开始实现）

## 概念 / 边界契约

### `item_name`

`item_name` 是本包唯一 P0 canonical business slot，用于 `/items` 新增项目名称。

允许用户说法：

| 用户说法 | canonical slot |
|---|---|
| 名称叫测试项目A | `item_name=测试项目A` |
| 项目名是测试项目A | `item_name=测试项目A` |
| 新增测试项目A | `item_name=测试项目A` |
| name 是测试项目A | `item_name=测试项目A` |

Intake 可以兼容别名，但 runtime 内部必须归一到 `item_name`。

### `value_slot`

`value_slot` 是 LearnedPath action JSON 上的参数绑定字段。P0 只允许绑定 fill action：

```json
{
  "action_type": "fill",
  "value": "测试项目A",
  "value_slot": "item_name"
}
```

P0 不新增数据库列；`value_slot` 写在 LearnedPath `actions` JSON 内。

### `slot_overrides`

`slot_overrides` 是执行阶段传入 replay 的运行时参数覆盖值：

```json
{
  "item_name": "测试项目B"
}
```

当 action 存在 `value_slot=item_name` 且 request 存在
`slot_overrides.item_name` 时，replay 必须使用 override 后的 B。

### Internal Runtime Adapter 边界

以下能力是内部代码步骤，不是 Application Skill：

- parameterize learned path actions。
- apply replay slot overrides。
- build effective replay action。

它们不得出现在 Router skill menu，也不得由 LLM agent 直接请求。Router 仍然只能推荐
业务级 `start_learning` / `start_replay`。

## 状态 / 结果契约

### 参数绑定结果

学习后参数化输出至少要能区分：

| status | 含义 |
---|---|
| `bound` | 至少一个 fill action 成功绑定 `value_slot=item_name` |
| `not_bound` | 未找到可绑定 action，不能标记为可参数化路径 |
| `skipped` | 本轮没有 `item_name`，不做本包参数化 |

### Replay override 结果

step log / debug trace 必须能表达：

| 字段 | 含义 |
---|---|
| `value_slot` | 当前 fill action 的参数槽，例如 `item_name` |
| `override_applied` | 是否应用了 runtime override |
| `effective_value` | 实际传给 `execute_action()` 的值，P0 `/items` 可明文 |

`effective_value` 明文日志只允许用于 P0 `/items` 非敏感测试字段。任何 credential /
token / secret slot 必须记录为 `<redacted>`。

## Schema / API 契约

### `ReplayRequest`

新增：

```python
class ReplayRequest(BaseModel):
    url: str
    slot_overrides: dict[str, str] = Field(default_factory=dict)
```

本包不加入 `evidence_targets`；那属于 11.3.5.5。

### `ReplayAction`

新增：

```python
class ReplayAction(BaseModel):
    step: int
    action_type: str
    target_selector: str | None = None
    target_description: str | None = None
    value: str | None = None
    value_slot: str | None = None
```

`_build_replay_actions()` 必须读取：

```python
value_slot=raw.get("value_slot")
```

### `run_replay()`

目标签名：

```python
def run_replay(
    learned_path: LearnedPath,
    url: str,
    *,
    headless: bool = True,
    slot_overrides: dict[str, str] | None = None,
) -> ReplayResult:
```

### Replay hook

`ReplayHandler` / `run_explicit_replay()` 必须支持把 `slot_overrides` 从 conversation
runtime 传到 `run_replay()`。

## Slot Override Propagation Path

P0 必须打通完整传播链：

1. Intake Agent 提取 `slots.item_name`。
2. Runtime `_fill_values_from_intake()` 生成 `fill_values.item_name`。
3. Learning branch 把 `fill_values` 传给 learning service。
4. Learning 后把匹配 fill action 写成 `value_slot=item_name`。
5. Execute branch 从本轮 `fill_values` 构造 `slot_overrides.item_name`。
6. `start_replay` / replay handler request 携带 `slot_overrides`。
7. `ReplayRequest` / replay service 接收 `slot_overrides`。
8. `run_replay()` 调 `_build_replay_actions()` 读取 `value_slot`。
9. `run_replay()` 在 `execute_action()` 前应用 override，生成 `effective_action`。
10. `execute_action()` 实际收到 `value=测试项目B`。
11. `wait_for_change_after_action()` 使用同一个 `effective_action`。
12. step log / debug trace 能证明使用的是 B，不是 A。

## Replay 安全规则

| 场景 | P0 处理 |
|---|---|
| action 有 `value_slot=item_name`，请求有 `slot_overrides.item_name` | 使用 override 值 |
| action 有 `value_slot=item_name`，请求缺 `slot_overrides.item_name` | 阻断，不使用固定录制值 |
| action 没有 `value_slot`，请求有 `slot_overrides.item_name` | 不替换 |
| 用户要求新增 B，但 path 没有 `value_slot=item_name` | Runtime 阻断，不调用 replay |
| 多个 fill action 匹配同一 slot | P0 可全部替换，但记录 warning |

阻断回复建议：

```text
我找到了已学习的“新增项目”路径，但它还不是可参数化路径，不能安全地把项目名替换成“测试项目B”。请重新学习一次新增项目操作。
```

## Evidence / Observation 契约

本包没有 DOM evidence / ExecutionEvidence contract 变化。

本包允许的 evidence 只有代码级验证证据：

- unit / integration test output。
- replay step log 中的 `value_slot`、`override_applied`、`effective_value`。
- mocked replay handler 收到的 `slot_overrides`。

不得把这些写成页面成功证据。DOM evidence 属于 11.3.5.5。

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：保持 code-owned Orchestrator / Runtime。LLM 只负责理解用户语言和建议，不直接执行 replay。
- Scope boundary 对齐：本包只改 `wagent chat` 参数化 replay 基础能力，不进入 recovery / abort / guided teaching。
- Roadmap / milestone 对齐：属于 11.3.5 working runtime P0 working loop 的参数化子包。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A，本包不改变权威产品模型。

## 兼容性契约

- 旧 `ReplayRequest(url=...)` 仍然有效，`slot_overrides` 默认为 `{}`。
- 旧 LearnedPath actions 没有 `value_slot` 仍可用于不需要 runtime 参数的 replay。
- 当用户提供 `item_name` 且旧 path 没有参数绑定时，chat runtime 必须阻断，不能静默回放固定值。
- 不新增 DB migration，不改变 LearnedPath 表结构。
- 不改变 ReplayResult status 枚举。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public conversation API contracts：不变，除非已有 replay API request schema 使用 `ReplayRequest`。
- Database schema：不变。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变。
- ExecutionEvidence contract：不变，留给 11.3.5.5。

## 非目标

- 不让 Router 输出 selector / Playwright action / learned_path_id。
- 不把 parameterizer / override adapter 注册成 Application Skill。
- 不接 TaskResultReporter。
- 不采集 DOM evidence。
- 不做 TaskPathPlanner。
- 不做 `pending_choice`。
- 不做 `learn_then_execute`。

## 未决问题

- `value_slot` 写回 existing dedup LearnedPath 的具体方式由实现阶段按现有 repository 边界确定；原则是只做 metadata-only merge，不覆盖用户已有 path 行为。

