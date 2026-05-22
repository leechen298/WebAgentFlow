# 契约（Contract）

状态：draft_for_review（文档已生成，未实现代码）

## 概念 / 边界契约

### WAgent Runtime Eval Runner

WAgent Runtime Eval Runner 是本地开发验收工具，用于通过 Conversation API 驱动
WebAgentFlow 的 runtime conversation path，并对结果做 hard gate 判定。

它不是产品内部 Agent，不是 TaskResultReporter，不是 Supervisor Agent，也不是
`verify-scenario` skill。它不能替产品生成 verdict，只能读取产品已经产生的 response、
events、history 和 LearnedPath 记录，并基于显式 gate 判定 eval case 是否通过。

### 运行入口

第一版必须提供：

```bash
pnpm run eval:wagent:items
```

可以同时提供：

```bash
pnpm run eval:wagent
```

默认配置：

| Config | Default | Override |
|---|---|---|
| API base | `http://127.0.0.1:8001` | `--api-base` |
| Product URL | `http://127.0.0.1:5176/items` | `--product-url` |
| Case | `items_closed_loop,single_path_direct_replay_regression` | `--case` |
| Timeout | 300 seconds | `--timeout` |
| Output dir | `artifacts/wagent-eval/` | `--artifact-dir` |
| Markdown result dir | `docs/testing/results/` | `--result-dir` |
| Browser visibility | `headless` | `--browser-visibility` |

Runner 不负责长期启动 API / product-test-site / Docker / Redis / PostgreSQL。服务不可用时
必须输出 blocked，而不是尝试隐式启动或继续判 fail。

### Conversation Driver Contract

Runner 必须通过 Conversation API 运行用例。允许调用：

```http
POST /conversation/sessions
POST /conversation/sessions/{session_id}/dispatch
GET /conversation/sessions/{session_id}
GET /conversation/sessions/{session_id}/messages
GET /conversation/sessions/{session_id}/events?limit=1000
GET /conversation/sessions/{session_id}/history
GET /exploration/learned-paths/{learned_path_id}
```

允许为了 discover LearnedPath 调用只读 catalog endpoint，例如：

```http
GET /exploration/learned-paths?page_template=/items&limit=10
```

禁止调用：

```http
POST /exploration/autonomous-runs
POST /exploration/autonomous-runs/stream
```

禁止直接调用 replay execution API 或内部 service 来代替 Conversation API dispatch。

### Session Contract

Runner 创建 session 时必须使用 runtime conversation 语义：

```json
{
  "current_mode": "interactive_chat",
  "metadata": {
    "client": "wagent_eval",
    "browser_visibility": "headless",
    "eval_runner": {
      "name": "wagent_runtime_eval",
      "schema_version": "11.3.6"
    }
  }
}
```

如果实际 API schema 使用不同字段名，实现必须按当前代码调整，但语义必须保持：

- session 是 interactive chat runtime session。
- metadata 能标识这是 eval runner。
- browser visibility 默认 headless。
- 不伪造内部 Agent identity。

### Case Contract

每个 eval case 必须有独立 record：

```json
{
  "case_id": "items_closed_loop",
  "status": "pass|fail|blocked|timeout|error",
  "turns": [],
  "events": [],
  "history": {},
  "learned_paths": [],
  "gates": []
}
```

Case status 派生规则：

| Case status | Rule |
|---|---|
| `pass` | 所有 required gates pass，warnings 不阻断 |
| `fail` | 至少一个 required gate fail |
| `blocked` | 环境或前置不可用，case 未能有效执行 |
| `timeout` | dispatch 或 evidence collection 超时 |
| `error` | runner 自身异常或无法解析关键 API response |

### Gate Contract

Gate 是 runner 的唯一判定单元。每个 gate 必须包含：

```json
{
  "name": "learned_path_created",
  "required": true,
  "status": "pass|fail|warning|not_observable|blocked",
  "evidence": "human-readable concise evidence",
  "source": "events|history|learned_path_detail|message|raw_api|preflight"
}
```

Gate status 语义：

| Gate status | Meaning |
|---|---|
| `pass` | 可审计证据满足 gate |
| `fail` | 可审计证据存在且不满足 gate |
| `warning` | 非阻断缺口或降级，例如 optional observability 缺失 |
| `not_observable` | 当前 public evidence 无法直接观察该字段 |
| `blocked` | 环境或前置条件阻断，不能判定 |

Required gate 只有 `pass` 才算通过。第一版允许 `effective_value_B` 在 step log 尚不可读时
降级为 warning / not_observable，但前提是 `slot_override_B`、DOM verified B 和
Reporter verified 都通过，并且 Markdown result 明确列出 follow-up。

### Case 1: `items_closed_loop`

流程：

```text
create interactive_chat session
send product URL, e.g. http://127.0.0.1:5176/items
send 学习新增项目，名称叫 测试项目A-${timestamp}
send 帮我新增项目，名称叫 测试项目B-${timestamp}
collect evidence
evaluate gates
```

Required gates：

| Gate | Required | Source | Rule |
|---|---|---|---|
| `session_created` | yes | raw API / session | session id exists |
| `pending_target_or_equivalent` | yes | session / events / history | URL turn leaves enough target context for learn turn |
| `learned_path_created` | yes | `chat_learning_completed` / history | new learned path id exists |
| `learned_path_parameterized` | yes | LearnedPath detail | fill action has `value_slot=item_name` |
| `execution_started` | yes | `chat_execution_started` | execution event exists |
| `slot_override_B` | yes | execution event | `slot_overrides.item_name == B` |
| `effective_value_B` | conditional | replay step log / history | fill effective value is B, not A |
| `evidence_target_item_list` | yes | execution evidence / LearnedPath | evidence target selector is `[data-testid='item-list']` |
| `dom_evidence_verified_B` | yes | execution evidence | `dom_text_present` verifies B |
| `reporter_verified` | yes | `task_result_reported` / history | `verification_outcome=verified` |
| `final_response_verified` | yes | final WAgent message | reply gives evidence-based success and references B |

### Case 2: `single_path_direct_replay_regression`

流程：

```text
reuse learned add-item path from items_closed_loop
send 帮我新增项目，名称叫 测试项目C-${timestamp}
collect evidence
evaluate gates
```

Required gates：

| Gate | Required | Source | Rule |
|---|---|---|---|
| `single_candidate_detected` | yes | events / history | one clear matched learned action |
| `no_pending_choice` | yes | events / session metadata | no A/B/C pending choice created |
| `no_planner_choice` | yes | events / history | no planner-backed choice path entered |
| `slot_override_C` | yes | execution event | `slot_overrides.item_name == C` |
| `dom_evidence_verified_C` | yes | execution evidence | `dom_text_present` verifies C |
| `reporter_verified` | yes | result event / history | `verification_outcome=verified` |
| `final_response_verified` | yes | final WAgent message | reply gives evidence-based success and references C |

### Deferred Case: `failure_recovery_menu_safety`

第一版不要求实现。原因：稳定触发需要 eval-only fault injection 或明确只读 fault hook。

后续实现前必须先新增 contract，至少覆盖：

- recovery menu wording。
- happy path must not show recovery menu。
- public payload / events 不泄露 private retry payload。
- injected failure 不能污染普通 runtime。

### Artifact Contract

JSON raw artifact：

```text
artifacts/wagent-eval/wagent-runtime-eval-${timestamp}.json
```

必须包含：

```json
{
  "schema_version": "11.3.6",
  "environment": {},
  "services": {},
  "config": {},
  "session_id": "...",
  "case_results": [],
  "turns": [],
  "events": [],
  "messages": [],
  "history": {},
  "learned_paths": [],
  "raw_api_responses": {},
  "gate_summary": {}
}
```

Markdown result：

```text
docs/testing/results/m11-11.3.6-wagent-runtime-eval-${date}.md
```

必须包含：

- Summary。
- Commit。
- API base。
- Product URL。
- Session ID。
- Cases table。
- Required gates table。
- Warnings / not observable。
- Raw artifact path。
- Not run / boundary statement。

### Exit Code Contract

| Exit code | Meaning |
|---:|---|
| 0 | all required gates pass |
| 1 | at least one required gate fail |
| 2 | environment blocked |
| 3 | timeout / dispatch did not return |
| 4 | artifact write failed |
| 5 | runner internal error |

If multiple conditions happen, runner should prefer the most actionable code in this order:

```text
artifact write failure > runner internal error > blocked > timeout > gate fail > pass
```

### Safety / Redaction Contract

Runner artifacts must not leak sensitive fields. For first-version `/items` cases,
`item_name` may appear because it is test data and required evidence. The following must be redacted
or excluded:

```text
credential
password
token
secret
cookie
authorization
api_key
private retry payload
pending_choice_private_map
raw ReplayAction private payload where selector / path id is not needed for the gate
```

Selectors may appear only when they are non-sensitive product-test-site selectors needed for gate
evidence, such as `[data-testid='item-list']`.

### Product / Milestone Contract

11.3.6 does not change:

- product lifecycle stages L1 / L2 / L3;
- internal Agent role table;
- Router / Orchestrator / Skill Runtime responsibility split;
- TaskResultReporter semantics;
- Failure Recovery semantics;
- LearnedPath storage contract;
- Conversation API response envelope;
- autonomous-run verification order.

11.3.6 adds only a local evaluation harness and its documentation.
