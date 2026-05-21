# 技术设计（Technical Design）

状态：ready_for_implementation（design review passed，未开始执行）

## 当前状态（Current State）

前置能力已经按 11.3.5.3 - 11.3.5.5 分包：

| 前置包 | 当前能力 |
|---|---|
| 11.3.5.3 | `apps/product-test-site` 有 `/items`，支持新增项目、列表展示、稳定 `data-testid` |
| 11.3.5.4 | `item_name` slot、`value_slot=item_name`、`slot_overrides.item_name`、`effective_action` |
| 11.3.5.5 | `evidence_targets`、`execution_evidence`、`TaskResultReporter` structured evidence verified path |

这些能力目前主要通过 targeted tests 验证。本包不新增主功能，而是把它们放到真实
`wagent chat` 产品入口里执行，并记录证据。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| 闭环必须从 `wagent chat` 进入 | 使用 CLI 创建 `interactive_chat` session 并发送用户消息 | `test-plan.md` CHAT-1 / CHAT-2 | 只读 API 只用于取证 |
| item name 必须唯一 | 执行脚本 / 手工步骤生成 timestamp 后缀 | `test-plan.md` DATA-1 | 防止历史文本假阳性 |
| 学习 A 后执行 B | 同一 session 依次发送 URL、学习、执行三类消息 | `test-plan.md` LOOP-1 | 不使用 direct replay API 代替 |
| replay 必须填入 B | 查询 events / history / step log 中的 `effective_value` | `test-plan.md` EV-3 | 如果明文被脱敏，至少记录 `value_slot` 和非敏感 P0 例外说明 |
| evidence 限定 item-list | 检查 `evidence_targets.selector` 和 `execution_evidence.target` | `test-plan.md` EV-4 | selector 是 `[data-testid='item-list']` |
| Reporter 必须 verified | 检查 `TASK_RESULT_REPORTED` event payload | `test-plan.md` EV-5 | replay `succeeded` 不等于 verified |
| 不能调用 autonomous run | 执行计划排除 `verify-scenario` 和 autonomous endpoints | `test-plan.md` NR-1 | 只使用 product chat path |

## 实现方案（Proposed Implementation）

本包默认只产生文档和测试结果 artifact：

```text
docs/iterations/m11/11.3.5.6-wagent-chat-items-closed-loop-evaluation/review.md
docs/testing/results/m11-11.3.5.6-items-closed-loop-<YYYY-MM-DD>.md
```

如果闭环执行失败：

- 环境或服务未启动：记录 `blocked`，不改 runtime。
- 前置实现缺失：记录缺口和最小复现，不扩大本包。
- 小的 wiring bug 阻断 P0：允许最小代码修复，但必须同步 review 说明、补 targeted test。
- 大功能缺口：记录为后续迭代，不在本包硬塞。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | 只读查询既有 conversation / learned-path endpoints | 不新增 route |
| API response schema | No | 使用既有 response 字段取证 | 不改变 schema |
| Database schema / migration | No | 读取 conversation / learned_paths 数据 | 不新增 migration |
| CLI | No | 使用既有 `wagent chat` | 不新增 CLI flag |
| Console UI | No | 不依赖 Console | N/A |
| Conversation events | No | 读取既有 events | 如果缺必要证据，记录缺口 |
| Replay execution | No by default | 通过 chat runtime 触发既有 replay | 失败时最多最小修复 |
| Reporter | No by default | 读取既有 TaskResultReporter outcome | 不改变 outcome enum |
| Worker / async jobs | No | 不涉及 worker | N/A |
| Tests / fixtures | Yes | 新增结果记录；可选最小 test/harness | 默认不新增自动化测试文件 |
| Docs | Yes | 新增本迭代文档和后续结果 artifact | 文档新增向后兼容 |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

No schema changes。

本包只读取：

- `ConversationReplaySummary.execution_evidence`
- conversation events payload
- LearnedPath actions JSON
- TaskResultReporter event payload

## 服务 / 模块设计（Service / Module Design）

### Service topology

本包执行时需要本地服务：

| Service | Command | Purpose |
|---|---|---|
| API | `pnpm run dev:api` | Conversation API、learning、replay |
| Product test site | `pnpm run dev:product` | `/items` target page |
| Infrastructure | `docker compose -f infra/docker/docker-compose.yml up -d` | PostgreSQL / Redis / MinIO |

如果本地已经有服务运行，应记录实际端口和健康检查结果，不强制重启。
`pnpm run dev:api` 和 `pnpm run dev:product` 是前台常驻进程，执行时必须分终端、
后台进程或复用已有服务，不要在同一个顺序 shell 中期待它们自动返回。

### Chat execution path

```text
wagent chat
-> POST /conversation/sessions
-> POST /conversation/sessions/{session_id}/dispatch
-> Entry Gate
-> Intake Agent
-> Context Collector
-> Router recommendation
-> Runtime Adjudicator
-> start_learning
-> LearnedPath value_slot=item_name
-> start_replay
-> run_replay effective_action
-> capture_execution_evidence
-> TaskResultReporter
-> WAgent response
```

### Required user inputs

`5176` 是本地示例端口，执行时应使用实际 product-test-site URL。

```text
http://127.0.0.1:5176/items
学习新增项目，名称叫测试项目A-${timestamp}
帮我新增项目，名称叫测试项目B-${timestamp}
:q
```

### Read-only evidence queries

执行后读取：

```bash
curl -s "http://127.0.0.1:8001/conversation/sessions/${SESSION_ID}/events?limit=1000"
curl -s "http://127.0.0.1:8001/conversation/sessions/${SESSION_ID}/history"
curl -s "http://127.0.0.1:8001/exploration/learned-paths?page_template=/items&limit=10"
```

如果 events / history 不能直接定位 LearnedPath id，允许从最新 `/items` LearnedPath
列表查找本轮记录，但必须在结果文件中说明匹配依据。

## 数据流（Data Flow）

```text
unique A/B names
  |
  v
wagent chat transcript
  |
  v
conversation session id
  |
  v
events / history / learned-path details
  |
  +--> learning evidence: learned_path_id + value_slot=item_name
  |
  +--> replay evidence: effective_value=B
  |
  +--> DOM evidence: dom_text_present verified target=B
  |
  +--> reporter evidence: outcome=verified
  |
  v
docs/testing/results/m11-11.3.5.6-items-closed-loop-<YYYY-MM-DD>.md
  |
  v
review.md summary
```

## 状态推导（Status / State Derivation）

Evaluation status 推导：

1. 环境无法启动或前置能力缺失 -> `blocked`。
2. 未能完整执行闭环，且没有足够失败证据 -> `unverified`。
3. 闭环执行完成但任一 required gate 失败 -> `fail`。
4. 所有 required gates 通过 -> `pass`。

不得因为 CLI exit 0 或 replay `succeeded` 单独推出 `pass`。

## 兼容性（Compatibility）

- 旧 conversation / replay / reporter 行为不变。
- 结果文件只新增文档，不影响运行时。
- 如果执行阶段需要最小代码修复，必须保持 11.3.5.3 - 11.3.5.5 contract 不变。

## 失败 / 边界情况（Failure / Edge Cases）

| Case | Handling |
|---|---|
| API unavailable | `blocked`，记录 health / connect error |
| product-test-site unavailable | `blocked`，记录 product URL 和错误 |
| learning 没生成 path | `fail` 或 `blocked`，按错误性质记录 |
| path 没有 `value_slot=item_name` | `fail`，不得继续当作 pass |
| replay 填入 A | `fail` |
| replay succeeded 但 evidence missing | `fail`，Reporter 应 `needs_review` / `uncertain` |
| Reporter outcome 非 `verified` | `fail` 或 `unverified`，按证据完整度记录 |
| event payload 缺少 step log | 不直接 fail，但必须通过其他可复查 evidence 证明 effective value；否则 `unverified` |

## 非目标（Non-goals）

- 不做 failure recovery 菜单。
- 不做多候选。
- 不做 TaskPathPlanner。
- 不做 additional CRUD 页面。
- 不做 autonomous exploration。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Preflight | 前置服务和实现能力存在 | `test-plan.md` PF-* |
| Chat closed loop | `wagent chat` 完成学习 A / 执行 B | `test-plan.md` LOOP-* |
| Evidence extraction | session / event / path / reporter 证据齐全 | `test-plan.md` EV-* |
| Negative boundary | 未调用 direct replay / autonomous | `test-plan.md` NR-* |
| Regression guard | targeted tests 仍通过 | `test-plan.md` REG-* |

## 验证命令入口（Validation Commands）

实际执行结果必须写入 `review.md` 和 `docs/testing/results/...`。

```bash
git status --short
pnpm --filter @web-agent-flow/product-test-site build
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_replay_hook.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_learned_path_replay.py
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_exploration_learned_paths_api.py -k replay
git diff --check
```
