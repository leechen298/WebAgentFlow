# 技术设计（Technical Design）

状态：draft_for_review（文档已生成，未实现代码）

## 当前状态（Current State）

当前代码和文档已经具备：

| Capability | Current state |
|---|---|
| Conversation API | 已支持 session create、dispatch、messages、events、history |
| `wagent conversation send` | 已有 session-targeted dispatch 能力 |
| `/items` product-test-site | 已作为 11.3.5.6 closed-loop validation 的产品级页面 |
| LearnedPath parameterization | `/items` add-item path 使用 `value_slot=item_name` 和 `slot_overrides` |
| ExecutionEvidence | 支持 `dom_text_present`、`[data-testid='item-list']`、verified target |
| TaskResultReporter adapter | 已能基于 replay result + DOM evidence 输出 `verification_outcome=verified` |
| Pending choice / planner choice | 已有 11.3.5.7 / 11.3.5.9 targeted coverage |
| Manual closed-loop result | 11.3.5.6 已有 Markdown 结果和 clean-slate evidence |

当前缺口是：没有一个稳定脚本把上述能力一次性跑完、采集证据、按 hard gate 判定并输出可审计
artifact。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry |
|---|---|---|
| 通过 Conversation API 驱动 | `ConversationDriver` 使用 `httpx` 调 create session + dispatch | API driver unit / smoke |
| 不调用 autonomous endpoints | runner request allowlist + tests / review grep | safety tests |
| 每个 case 独立 gate | `EvalCaseResult` + `GateResult` dataclasses | gate evaluator tests |
| required gates 硬判定 | status reducer derives final exit code | exit-code tests |
| raw artifact 可审计 | JSON writer preserves raw responses and normalized evidence | artifact tests |
| Markdown report 可读 | Markdown writer reads same normalized result | report tests |
| public / private payload 安全 | redaction pass before artifact write | redaction tests |
| no Codex subjective pass | final status only from gate statuses and exit code | review / tests |

## 实现方案（Proposed Implementation）

### 1. 文件结构

Planned files:

```text
scripts/evals/wagent_runtime_eval.py
docs/testing/wagent-runtime-eval.md
package.json
```

Optional only if the runner becomes too large:

```text
scripts/evals/lib/
```

第一版优先单文件 runner，使用 internal classes / dataclasses 保持结构清晰。不要把 runner
放进 `apps/api/tests`，因为它跨 API、product-test-site、Conversation runtime、artifacts
和 result docs。

### 2. Runner modules

单文件内建议保持五层结构：

```text
Config / CLI args
ConversationDriver
EvidenceCollector
GateEvaluator
ArtifactWriter
main / exit reducer
```

#### Config / CLI args

支持参数：

```text
--api-base
--product-url
--case
--timeout
--artifact-dir
--result-dir
--browser-visibility
--no-markdown
--json-only
```

第一版默认 case set：

```text
items_closed_loop
single_path_direct_replay_regression
```

`--case items_closed_loop` 可只跑单个 case，便于开发调试。

#### ConversationDriver

职责：

- `create_session()`
- `send_turn(session_id, text)`
- 记录 request / response / duration / HTTP status / errors。
- timeout 显式转换成 case `timeout`。

建议使用 `httpx.Client(timeout=httpx.Timeout(timeout))` 或 async equivalent。第一版可以用同步
client，减少复杂度。

#### EvidenceCollector

职责：

- `get_session(session_id)`
- `get_messages(session_id)`
- `get_events(session_id, limit=1000)`
- `get_history(session_id)`
- `get_learned_path_detail(learned_path_id)`
- 从 events / history 中提取 learned_path_id、execution events、reporter events。

EvidenceCollector 不做 pass / fail 判定，只做解析和 normalize。

#### GateEvaluator

职责：

- `evaluate_items_closed_loop(context)`
- `evaluate_single_path_direct_replay_regression(context)`
- 输出 `GateResult[]`。
- 聚合 case status。

GateEvaluator 必须从结构化 evidence 判断，不得只靠 final text。
Final WAgent response 只能作为 `final_response_verified` gate，不得代替 DOM evidence 或
TaskResultReporter gate。

#### ArtifactWriter

职责：

- 写 JSON raw artifact。
- 写 Markdown result。
- 运行 redaction。
- artifact 写入失败返回 exit `4`。

Markdown writer 必须基于同一个 normalized eval result，不能重新解析 raw responses 生成不同结论。

### 3. Data model

建议 dataclasses：

```python
@dataclass
class GateResult:
    name: str
    required: bool
    status: str
    evidence: str
    source: str

@dataclass
class TurnRecord:
    text: str
    started_at: str
    duration_ms: int
    response: dict[str, Any] | None
    error: str | None = None

@dataclass
class CaseResult:
    case_id: str
    status: str
    turns: list[TurnRecord]
    gates: list[GateResult]
    warnings: list[str]
```

可以直接转 dict 写 JSON，避免引入额外依赖。

### 4. Preflight

Preflight 必须做：

```http
GET {api_base}/health
GET {product_url}
```

API health 必须返回可用 response。Product URL 可接受 2xx；如 Vite dev server 返回 HTML，也视为
可用。

Preflight 不启动服务。blocked result 需写入：

- API base。
- Product URL。
- failed check。
- status code / error。
- suggested commands。

### 5. Case flow

#### `items_closed_loop`

Pseudo-flow：

```python
stamp = current_timestamp()
learn_name = f"测试项目A-{stamp}"
exec_name = f"测试项目B-{stamp}"

session = create_session()
send_turn(product_url)
send_turn(f"学习新增项目，名称叫 {learn_name}")
send_turn(f"帮我新增项目，名称叫 {exec_name}")

evidence = collect_all(session_id)
learned_path_id = extract_new_learned_path_id(evidence)
learned_path = get_learned_path_detail(learned_path_id)
gates = evaluate_items_closed_loop(evidence, learned_path, exec_name)
```

The URL turn can produce a "need learning" style reply. That is acceptable if the subsequent learn turn
can use the target context. `pending_target_or_equivalent` should be evaluated from session metadata,
events, or successful downstream learning evidence.

#### `single_path_direct_replay_regression`

Pseudo-flow：

```python
exec_name_c = f"测试项目C-{stamp}"
send_turn(f"帮我新增项目，名称叫 {exec_name_c}")
evidence = collect_all(session_id)
gates = evaluate_single_path_direct_replay(evidence, exec_name_c)
```

This case should run after `items_closed_loop` in the same session by default. It may run in a new
session later only if runner has an explicit way to seed or reference the learned path without bypassing
Conversation API.

### 6. Gate extraction details

Recommended event extraction:

| Evidence | Event / Source |
|---|---|
| new learned path id | `chat_learning_completed.payload.new_learned_path_id` |
| execution start | `chat_execution_started` |
| slot override | `chat_execution_started.payload.slot_overrides.item_name` |
| execution evidence | `chat_execution_completed.payload.execution_evidence` or history replay summary |
| reporter outcome | `task_result_reported.payload.verification_outcome` |
| final response | latest assistant message after dispatch |
| pending choice absence | no `pending_choice_created` / no `planner_choice_created` after C turn |
| planner absence | no planner choice event after C turn |

If event type names differ in current code, implementation may adapt, but `contract.md` gate semantics
must remain stable.

### 7. Step log observability

If current history / events expose replay step logs with:

```text
value_slot
override_applied
effective_value
```

runner should hard-check `effective_value_B` and `effective_value_C`.

If not exposed, runner must:

- mark `effective_value_B` as `not_observable` or `warning`;
- keep the case pass only if `slot_override_B`, DOM verified B and Reporter verified pass;
- record follow-up: expose read-only sanitized replay step logs through `chat_execution_completed`
  replay summary or history replay summary.

Do not make runner infer `effective_value` from final text alone.

### 8. Redaction

Implement a recursive redaction helper before artifact write:

```python
SENSITIVE_KEYS = {
    "password",
    "credential",
    "token",
    "secret",
    "cookie",
    "authorization",
    "api_key",
    "pending_choice_private_map",
    "private_retry_payload",
}
```

For `/items`, `item_name` values may remain visible because they are test-generated evidence. If later
cases include credentials or login, the case must define slot-specific redaction before joining this runner.

### 9. Markdown report

Markdown report skeleton:

```markdown
# M11.3.6 WAgent Runtime Eval Result

Date:
Status:
Commit:
API Base:
Product URL:
Session ID:
JSON Artifact:

## Cases

| Case | Status | Required Gates | Warnings |
|---|---|---|---|

## Required Gates

| Case | Gate | Status | Evidence | Source |
|---|---|---|---|---|

## Warnings / Not Observable

## Not Run / Boundary
```

### 10. Package script

Add root script:

```json
{
  "scripts": {
    "eval:wagent:items": ".venv/bin/python scripts/evals/wagent_runtime_eval.py --case items_closed_loop --case single_path_direct_replay_regression",
    "eval:wagent": ".venv/bin/python scripts/evals/wagent_runtime_eval.py"
  }
}
```

If current package script style prefers one command only, add `eval:wagent:items` first and leave
`eval:wagent` for a follow-up.

## Test Matrix Alignment

Implementation tests should verify:

- CLI args parse defaults.
- preflight returns blocked on unreachable services.
- gate evaluator passes with synthetic valid evidence.
- gate evaluator fails when required evidence is missing.
- `effective_value` missing becomes warning / not_observable, not guessed pass.
- redaction removes sensitive keys from artifacts.
- exit reducer maps statuses to codes.
- Markdown report and JSON artifact derive from same result object.

Live eval run is not required for initial unit-level implementation, but before closeout this package should run
against local services if available and record the exact result artifact in `review.md`.

## Compatibility / Rollback

Runner is additive:

- no DB migration;
- no API schema change by default;
- no runtime service behavior change by default;
- no Console UI change.

Rollback is deleting the runner script, docs, and package script. Generated artifacts under
`artifacts/wagent-eval/` should remain untracked unless the repo already tracks such evidence files.
