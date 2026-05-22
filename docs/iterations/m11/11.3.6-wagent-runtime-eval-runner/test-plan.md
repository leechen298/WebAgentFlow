# 测试计划（Test Plan）

状态：draft_for_review（文档已生成，未实现代码）

## 适用条件

本包新增本地 eval runner，涉及 live Conversation API、product-test-site、browser-backed
learning / replay、TaskResultReporter evidence、artifact 输出和 exit code，因此必须维护
`test-plan.md`。

## 测试范围（Test Scope）

- Unit：CLI args、preflight reducer、gate evaluator、redaction、exit code reducer、
  Markdown / JSON writer。
- Integration：runner 对 Conversation API 的 create session / dispatch / evidence collection。
- API：只读 session / messages / events / history / LearnedPath detail。
- Product site：`apps/product-test-site` `/items` 页面。
- Console UI：N/A。
- Live `wagent chat`：N/A，runner 直接调用 Conversation API。
- Live autonomous run：N/A，明确禁止。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Unit | UT-1 CLI default args | runner parser | api/product/cases/default timeout set | Yes | no network |
| Unit | UT-2 preflight blocked API | preflight function | status blocked, exit 2 candidate | Yes | mocked http |
| Unit | UT-3 preflight blocked product | preflight function | status blocked, product error recorded | Yes | mocked http |
| Unit | UT-4 gate pass from valid evidence | GateEvaluator | required gates pass | Yes | synthetic events |
| Unit | UT-5 missing required evidence fails | GateEvaluator | gate fail, case fail | Yes | hard gate |
| Unit | UT-6 effective value unavailable warning | GateEvaluator | not_observable / warning | Yes | no guessing |
| Unit | UT-7 single path no planner | GateEvaluator | no pending/planner choice pass | Yes | synthetic C turn |
| Unit | UT-8 redaction | ArtifactWriter | sensitive keys redacted | Yes | artifact safety |
| Unit | UT-9 exit reducer | status reducer | pass=0, fail=1, blocked=2, timeout=3 | Yes | deterministic |
| Unit | UT-10 markdown from normalized result | writer | report matches gate statuses | Yes | no reparsing |
| Integration | IN-1 API health | `GET /health` | reachable | Yes for live run | preflight |
| Integration | IN-2 product `/items` reachable | `GET /items` | reachable | Yes for live run | preflight |
| Integration | IN-3 create session | Conversation API | session id exists | Yes for live run | no CLI chat |
| Integration | IN-4 dispatch URL / learn A / execute B | Conversation API | responses returned | Yes for live run | timeout 300s |
| Integration | IN-5 collect events/history/path | read-only APIs | evidence collected | Yes for live run | no direct replay |
| Case | CASE-1 `items_closed_loop` | runner | required gates pass or explicit fail | Yes | first case |
| Case | CASE-2 `single_path_direct_replay_regression` | runner | direct replay verified, no choice/planner | Yes | second case |
| Artifact | ART-1 JSON written | filesystem | file exists, schema_version 11.3.6 | Yes | if run starts |
| Artifact | ART-2 Markdown written | filesystem | result path exists | Yes | unless `--no-markdown` |
| Safety | SAF-1 no autonomous request | code / logs | no autonomous-run endpoint call | Yes | grep / review |
| Safety | SAF-2 no private payload leak | JSON / Markdown | sensitive fields redacted | Yes | review artifact |
| Safety | SAF-3 no Codex subjective pass | report | status derives from gates | Yes | review |

## 推荐命令

### Static / unit stage

After implementation, run the runner's unit tests if a dedicated test file is added:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_runtime_eval.py -q
```

If the runner tests live outside `apps/api/tests`, use the repo's chosen path and record the exact command in
`review.md`.

Run Python lint on the runner:

```bash
uv run ruff check scripts/evals/wagent_runtime_eval.py
```

Check formatting / whitespace:

```bash
git diff --check
```

### Service preflight for live eval

Runner does not start services. Start them separately if needed:

```bash
docker compose -f infra/docker/docker-compose.yml up -d
pnpm run db:migrate:api
pnpm run dev:api
pnpm run dev:product
```

`pnpm run dev:api` and `pnpm run dev:product` are foreground long-running processes. Use separate
terminals or managed background processes.

Manual health checks:

```bash
curl -sI "http://127.0.0.1:8001/health"
curl -sI "http://127.0.0.1:5176/items"
```

### Live eval

```bash
pnpm run eval:wagent:items
```

Expected if services are healthy and runtime works:

```text
status=pass
exit code 0
JSON artifact written under artifacts/wagent-eval/
Markdown result written under docs/testing/results/
```

Expected if API or product site is unavailable:

```text
status=blocked
exit code 2
blocked result explains failed preflight
```

## Required Gate Review

For a live pass, `review.md` must record at least:

| Evidence | Required |
|---|---|
| command | yes |
| exit code | yes |
| JSON artifact path | yes |
| Markdown result path | yes |
| session id | yes |
| `items_closed_loop` gate summary | yes |
| `single_path_direct_replay_regression` gate summary | yes |
| warnings / not_observable | yes, if any |
| not-run / boundary statement | yes |

## 不运行 / 不声明

| Item | Reason | Follow-up |
|---|---|---|
| `verify-scenario` | 本包验证 Conversation runtime eval runner，不走 autonomous verification skill | 不运行 |
| autonomous run | AGENTS 边界禁止非产品 UI / 非 verify-scenario 直接调用 | 不运行 |
| Console UI smoke | 本包是 API-driven eval runner | 用户显式要求时另开 UI smoke |
| login page | 敏感输入、登录态、cookie、重定向、验证码风险过高 | 后续单独设计 |
| failure recovery injection | 第一版没有稳定 fault hook | v2 独立 contract |
| pending choice multi-candidate live eval | 第一版只保核心 two cases | 后续扩展 |
| planner-backed choice live eval | 第一版只保护 single-path bypass Planner | 后续扩展 |

## 验收门槛

实现阶段不得只提交脚本框架。必须证明：

```text
runner can create conversation session
runner can dispatch URL / learn A / execute B
runner can collect evidence through read-only APIs
runner can hard-check required gates
runner can detect direct replay regression for C
runner can write JSON + Markdown artifacts
runner exit code matches gate outcome
runner does not call autonomous-run endpoints
runner does not leak private payloads into public artifacts
```

如果 live services 不可用，允许本包先以 unit / mocked integration 收口，但 `review.md` 必须把
live eval 标成 blocked / not run，不能声称 runtime eval pass。
