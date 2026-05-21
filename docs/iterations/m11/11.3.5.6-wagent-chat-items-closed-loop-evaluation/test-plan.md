# 测试计划（Test Plan）

状态：draft_docs（待评审，未开始执行）

## 适用条件

本包涉及 live `wagent chat` 产品入口、browser-backed replay、Reporter evidence 和
Codex / AI 外部测试操作员边界，必须维护 `test-plan.md`。

## 测试范围（Test Scope）

- Unit：前置 targeted tests 必须保持通过。
- Integration：conversation runtime / replay hook / reporter targeted tests。
- API：只读 conversation events / history / LearnedPath 查询用于取证。
- Console UI：N/A，本包不依赖 Console。
- E2E：`wagent chat` 到 `/items` product-test-site 的 closed-loop evaluation。
- Agent / Reporter / Recovery：只验证 TaskResultReporter outcome；不做 recovery。
- Codex / AI External Operator：允许 Codex 操作 `wagent chat` 并记录真实输出。
- Live autonomous run：N/A，明确禁止。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Preflight | PF-1 git state | `git status --short --branch` | 清楚记录当前 commit / dirty state | Yes | 执行前记录 |
| Preflight | PF-2 product build | `pnpm --filter @web-agent-flow/product-test-site build` | build passed | Yes | 证明 `/items` 可构建 |
| Preflight | PF-3 targeted runtime tests | pytest targeted suite | 11.3.5.4 / 11.3.5.5 targeted tests passed | Yes | 不代替 live loop |
| Preflight | PF-4 services reachable | API health + product URL | API 8001 / product URL 可访问 | Yes | 端口以实际为准 |
| Chat | LOOP-1 create chat session | `wagent chat --headless` | 输出 session id | Yes | 记录 session id |
| Chat | LOOP-2 target URL turn | 输入 `/items` URL | 系统记住或进入目标上下文 | Yes | 可接受追问 |
| Chat | LOOP-3 learn A | 输入学习新增项目 A | 学习完成，生成 LearnedPath | Yes | A 必须唯一 |
| Chat | LOOP-4 execute B | 输入执行新增项目 B | WAgent 执行并回复 evidence-based 结果 | Yes | B 必须唯一 |
| Evidence | EV-1 LearnedPath binding | `GET /exploration/learned-paths/{id}` | actions JSON 含 `value_slot=item_name` | Yes | path id 来源需说明 |
| Evidence | EV-2 slot override | events / history | `slot_overrides.item_name=B` | Yes | 若字段缺失需记录缺口 |
| Evidence | EV-3 effective value | step log / event / history | fill action effective value 是 B | Yes | 不得是 A |
| Evidence | EV-4 DOM evidence | `execution_evidence` | `dom_text_present verified target=B` | Yes | selector 应为 item-list |
| Evidence | EV-5 Reporter | task result event | `verification_outcome=verified` 或 report outcome verified | Yes | replay succeeded 不够 |
| Evidence | EV-6 final response | CLI transcript | 回复说明看到了 B 并确认新增成功 | Yes | 必须是保守证据话术 |
| Negative | NR-1 no autonomous | process / command log | 未调用 `verify-scenario` 或 autonomous run | Yes | 记录 not run |
| Negative | NR-2 no direct replay substitution | command log | 不把 direct replay API 当闭环入口 | Yes | 只读 API 查询可用 |

## 推荐执行命令

### 1. 前置验证

```bash
git status --short --branch
pnpm --filter @web-agent-flow/product-test-site build

cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_replay_hook.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_learned_path_replay.py

PYTHONPATH=. ../../.venv/bin/pytest tests/test_exploration_learned_paths_api.py -k replay
```

### 2. 启动本地服务

如果服务未启动：

```bash
docker compose -f infra/docker/docker-compose.yml up -d
pnpm run db:migrate:api
pnpm run dev:api
pnpm run dev:product
```

也可以使用已有服务，但必须记录实际 API base 和 product URL。

Health / route checks：

```bash
curl -sI "http://127.0.0.1:8001/health"
curl -sI "http://127.0.0.1:5176/items"
```

### 3. 执行 `wagent chat` 闭环

`5176` 只是示例端口。执行时按实际 product-test-site URL 设置 `ITEMS_URL`。

```bash
export ITEMS_URL="http://127.0.0.1:5176/items"
export RUN_STAMP="$(date +%Y%m%d%H%M%S)"
export LEARN_NAME="测试项目A-${RUN_STAMP}"
export EXEC_NAME="测试项目B-${RUN_STAMP}"

printf '%s\n' \
  "${ITEMS_URL}" \
  "学习新增项目，名称叫${LEARN_NAME}" \
  "帮我新增项目，名称叫${EXEC_NAME}" \
  ":q" \
  | .venv/bin/wagent chat --api-base "http://127.0.0.1:8001" --headless
```

必须保存完整 stdout / stderr 到结果文件，或在执行时使用 `tee` 写入临时 log，并把关键行摘录到
`docs/testing/results/...`。

### 4. 读取只读证据

从 CLI 输出提取 `SESSION_ID` 后：

```bash
curl -s "http://127.0.0.1:8001/conversation/sessions/${SESSION_ID}/events?limit=1000"
curl -s "http://127.0.0.1:8001/conversation/sessions/${SESSION_ID}/history"
curl -s "http://127.0.0.1:8001/exploration/learned-paths?page_template=/items&limit=10"
```

如果拿到 `LEARNED_PATH_ID`：

```bash
curl -s "http://127.0.0.1:8001/exploration/learned-paths/${LEARNED_PATH_ID}"
```

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 本包的 E2E 是 CLI product entry E2E，不是 Console UI smoke。
- 如果没有真实运行 `wagent chat`，不得声称 closed loop passed。
- 如果只运行 API / pytest，不得写成 E2E pass。
- 如果使用 visible browser 辅助观察，必须记录它只是辅助观察；pass 仍以 required gates 为准。

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

Codex / AI 可以操作 `wagent chat`，但只能记录真实输出：

- 实际命令。
- session id。
- 用户输入。
- WAgent 回复。
- events / history / LearnedPath 查询输出摘要。
- pass / fail / blocked / unverified 推导。

不得生成内部 Agent verdict，不得替 TaskResultReporter 编造 outcome。

## Live Run 边界（Live Run Boundary）

本包不运行：

- `verify-scenario`
- `POST /exploration/autonomous-runs`
- `POST /exploration/autonomous-runs/stream`
- in-process `run_autonomous_exploration`

如果有人误运行，必须记录为越界，不得作为本包通过证据。

## 结果文件模板

执行完成后创建：

```text
docs/testing/results/<YYYY-MM-DD>-11-3-5-6-items-closed-loop.md
```

最低内容：

```markdown
# 11.3.5.6 `/items` Closed-loop Result

Date:
Commit:
evaluation_status:
API base:
Product URL:
Session ID:
Learn item name:
Execute item name:
LearnedPath ID:

## Commands

## Transcript

## Evidence

| Gate | Expected | Actual | Status | Source |
|---|---|---|---|---|

## Reporter Outcome

## Not Run

## Follow-ups
```

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| `verify-scenario` | 本包验证 `wagent chat` 产品入口，不走 verification skill | 无；这是明确边界 |
| autonomous run | 本包不是 L1 autonomous learning | 无；禁止越界 |
| TaskPathPlanner multi-candidate | 属于 11.3.5.9 | 多候选能力后续验证 |
| Failure Recovery | 属于 11.3.5.8 | 失败出口后续补 |
