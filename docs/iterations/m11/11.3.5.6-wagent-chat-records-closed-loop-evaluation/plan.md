# 实施计划（Implementation Plan）

状态：implementation complete（closed-loop pass，result recorded）

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md)
- [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md)

## 文件 / 模块

默认只新增或更新文档结果：

- `docs/iterations/m11/11.3.5.6-wagent-chat-records-closed-loop-evaluation/review.md` - 记录设计评审、执行结果和未运行项。
- `docs/testing/results/m11-11.3.5.6-records-closed-loop-<YYYY-MM-DD>.md` -
  记录完整闭环证据。

如发现阻断性小缺口，允许最小代码修复，但必须：

- 先说明偏离原因。
- 补 targeted test。
- 记录到 `review.md`。
- 不扩大到 11.3.5.7 / 11.3.5.8 / 11.3.5.9 范围。

## 步骤

### Step 0 · 设计评审

- 本包七件套已通过设计评审。
- 11.3.5.6 已确认是 evaluation / evidence 包，不是新功能包。
- 当前状态已收口为
  `implementation complete（closed-loop pass，external review passed）`。

### Step 1 · 前置能力检查

运行：

```bash
git status --short --branch
rg -n "slot_overrides|value_slot|effective_action|execution_evidence|evidence_targets" \
  apps/api/app apps/api/tests
rg -n "record-list|record-create-button|record-name-input" \
  apps/fixture-site/src/pages/ItemsPage.vue
```

确认：

- 11.3.5.3 `/records` 页面存在。
- 11.3.5.4 参数化 replay 存在。
- 11.3.5.5 evidence / reporter 存在。

### Step 2 · Targeted regression

运行前置 targeted tests：

```bash
pnpm --filter @web-agent-flow/fixture-site build

cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_replay_hook.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_learned_path_replay.py

PYTHONPATH=. ../../.venv/bin/pytest tests/test_exploration_learned_paths_api.py -k replay
```

如果失败：

- 先记录失败。
- 如果是前置包回归，最小修复并补测试。
- 如果是环境问题，标记 `blocked`。

### Step 3 · 启动服务

确认或启动：

```bash
docker compose -f infra/docker/docker-compose.yml up -d
pnpm run db:migrate:api
pnpm run dev:api
pnpm run dev:product
```

`pnpm run dev:api` 和 `pnpm run dev:product` 是前台常驻进程。执行时需要分终端、
后台进程、任务管理器或复用已有服务；不要在同一个顺序 shell 中期待它们自动返回。

记录实际：

- API base。
- Product URL。
- health / route check 输出。
- 是否复用了已有服务。

### Step 4 · 执行 `wagent chat` 闭环

使用唯一名称：

```bash
export ITEMS_URL="http://127.0.0.1:<fixture-port>/records"
export RUN_STAMP="$(date +%Y%m%d%H%M%S)"
export LEARN_NAME="测试项目A-${RUN_STAMP}"
export EXEC_NAME="测试项目B-${RUN_STAMP}"
```

执行：

```bash
printf '%s\n' \
  "${ITEMS_URL}" \
  "学习新增项目，名称叫${LEARN_NAME}" \
  "帮我新增项目，名称叫${EXEC_NAME}" \
  ":q" \
  | .venv/bin/wagent chat --api-base "http://127.0.0.1:8001" --headless
```

保存：

- 完整 stdout。
- 完整 stderr。
- exit code。
- session id。

### Step 5 · 取证

查询只读证据：

```bash
curl -s "http://127.0.0.1:8001/conversation/sessions/${SESSION_ID}/events?limit=1000"
curl -s "http://127.0.0.1:8001/conversation/sessions/${SESSION_ID}/history"
curl -s "http://127.0.0.1:8001/exploration/learned-paths?page_template=/records&limit=10"
```

必要时查询 LearnedPath detail：

```bash
curl -s "http://127.0.0.1:8001/exploration/learned-paths/${LEARNED_PATH_ID}"
```

检查：

- `value_slot=record_name`。
- `slot_overrides.record_name=${EXEC_NAME}`。
- replay fill step effective value 是 `${EXEC_NAME}`。
- evidence target / evidence target 是 `${EXEC_NAME}`。
- `verification_outcome=verified` 或 report outcome verified。
- final response 不只是“执行完成”，而是说明看到了 `${EXEC_NAME}`。

### Step 6 · 写结果文件

新增：

```text
docs/testing/results/m11-11.3.5.6-records-closed-loop-<YYYY-MM-DD>.md
```

必须包含：

- Commit hash。
- Commands。
- Transcript。
- Session id。
- LearnedPath id。
- Evidence table。
- evaluation_status。
- Not run。
- Follow-ups。

### Step 7 · 写回 review

更新本包 `review.md`：

- 设计评审结论。
- 执行时间。
- 结果文件链接。
- Required gates 表。
- 失败 / blocked / unverified 原因。
- 未运行项。

### Step 8 · Hygiene

运行：

```bash
git diff --check
```

如果本包做了代码修复，再运行对应 scoped ruff / pytest，并在 `review.md` 写明。

## 验证

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `pnpm --filter @web-agent-flow/fixture-site build` | `/records` target page 可构建 | Yes | product site build |
| API targeted pytest suite | 参数化 replay / evidence / reporter targeted tests 仍通过 | Yes | 见 `test-plan.md` |
| `wagent chat --headless` scripted run | 真实 chat session 完成学习 A / 执行 B | Yes | 本包核心 |
| `GET /conversation/.../events` | runtime events 可复查 | Yes | 只读取证 |
| `GET /exploration/learned-paths/{id}` | LearnedPath actions 可复查 | Yes | 只读取证 |
| `git diff --check` | 文档 / 代码 diff clean | Yes | hygiene |

## 复核清单（Review Checklist）

- [ ] 实现仍然匹配 `contract.md`。
- [ ] 没有把 direct replay API 当作闭环入口。
- [ ] 没有运行 `verify-scenario` 或 autonomous run。
- [ ] `LEARN_NAME` 和 `EXEC_NAME` 唯一。
- [ ] `value_slot=record_name` 已确认。
- [ ] effective value 是 B，不是 A。
- [ ] evidence target 是 B。
- [ ] Reporter outcome 是 `verified`。
- [ ] final WAgent response 是 evidence-based 成功回复。
- [ ] 结果文件已写入 `docs/testing/results/`。
- [ ] `review.md` 已记录实际证据和未运行项。
