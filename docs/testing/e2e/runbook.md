# 确定性 E2E 运行说明

WebAgentFlow 使用 Playwright Test 做浏览器 E2E 和 API request 验证。
E2E workspace 位于 `apps/e2e/`。

E2E 用例按产品能力域组织在 `apps/e2e/tests/` 下，例如
`apps/e2e/tests/replay/` 和 `apps/e2e/tests/conversation/`。这些用例是跨
console、API、数据库、外部 Fixture-Site 和后端 Playwright replay 的产品闭环测试。
它们不是 console 前端单元测试，不应放到 `apps/console/src/__tests__/`。

## 当前覆盖

当前 E2E 覆盖已经完成的能力：

- M10.2 LearnedPath replay API。
- M10.2 LearnedPath catalog UI replay 区块。
- M10.2 LearnedPath catalog list / trust filter / drawer / replay section presence。
- M11.0 conversation runtime explicit replay smoke。
- M11.0 `wagent conversation` CLI-driven explicit replay smoke。
- External fixture manifest ingestion for replay-backed product E2E.

这不会新增产品行为，也不会扩大 M10.2 范围。

Replay 测试域的长期矩阵见 [`../features/replay.md`](../features/replay.md)。
Conversation 测试域的长期矩阵见
[`../features/conversation.md`](../features/conversation.md)。确定性 E2E 轨道见
[`README.md`](README.md)。Agent-operated UI exploratory 规程见
[`../agent-operated-ui/README.md`](../agent-operated-ui/README.md)。Replay 探索式
补充用例见 [`../exploratory/replay-e2e-cases.md`](../exploratory/replay-e2e-cases.md)。

注意：确定性 E2E 通常以 headless Playwright Test 运行。它可以证明自动化回归通过，
但不能冒充 Agent-operated UI exploratory。若报告声称完成了 Agent-operated UI
exploratory，必须使用 Codex、Claude Code 或其他浏览器能力工具，或 headed Playwright
打开真实页面，并记录可见 UI 操作证据。

## 环境组成

第一版默认由开发者手动启动依赖服务：

- FastAPI server。
- 外部 Fixture-Site。
- console。
- 已完成 schema 迁移并写入 E2E seed 数据的 PostgreSQL。

Playwright config 暂时不使用 `webServer` 编排全部服务。等回归轨道稳定后，
后续再考虑自动编排。

按以下顺序运行确定性 E2E：

1. 启动 Docker 基础设施：`pnpm run docker:up`。
2. 执行 API 数据库迁移：`pnpm run db:migrate:api`。
3. 启动 API server：`API_PORT=8001 pnpm run dev:api`。
4. 从独立仓库启动外部 Fixture-Site：
   `cd /Users/leechen/projects/WebAgentFlow-Fixture-Site && pnpm dev`。
5. 启动 console：
   `VITE_USE_DEV_PROXY=true API_PORT=8001 CONSOLE_PORT=5174 pnpm run dev:console`。
6. 配置显式 spec root：
   `export WAF_PAGE_SPEC_ROOT=/path/to/WebAgentFlow-Fixture-Site/web/specs`。
7. 如需运行 legacy replay E2E，从外部 Fixture-Site provider 显式 opt-in
   写入本地 raw replay 固定数据：
   `python3 evals/seed-webagentflow-replay-fixtures.py --webagentflow-local-seed`。
8. 运行 E2E：`pnpm run test:e2e`。

`WAF_PAGE_SPEC_ROOT` 是 page verification 的显式 spec 来源。只有列出或加载
page verification specs 时需要；API 启动和 `/health` 不需要它。E2E target URL
来自外部 provider 生成的本地 ignored `apps/e2e/.tmp/replay-fixtures.json`。
该 raw 文件不是 WebAgentFlow 可提交的 provider 验收摘要；可提交摘要应使用
Fixture-Site 的 redacted provider summary。

首次运行前，用 `pnpm run test:e2e:install` 安装 Playwright Test Chromium
浏览器。如果该命令卡在 `playwright install chromium`，通常是浏览器下载或网络
环境问题。可以稍后重试；如果本机已经有 Chromium 缓存，确定性 E2E 仍可能正常运行。

查看 [`../results/2026-05-11-replay-e2e-rerun.md`](../results/2026-05-11-replay-e2e-rerun.md)
了解历史 replay E2E rerun 证据；查看
[`../results/2026-05-11-learned-path-catalog-deterministic-e2e.md`](../results/2026-05-11-learned-path-catalog-deterministic-e2e.md)
了解 LearnedPath catalog deterministic E2E 扩展结果；查看
[`../results/2026-05-11-conversation-runtime-e2e.md`](../results/2026-05-11-conversation-runtime-e2e.md)
了解 M11 conversation runtime E2E 首次 smoke 结果；查看
[`../results/2026-05-11-conversation-cli-e2e.md`](../results/2026-05-11-conversation-cli-e2e.md)
了解 `wagent conversation` CLI-driven E2E 结果。

`apps/e2e/test-results/` 和 `apps/e2e/playwright-report/` 是 Playwright
原始输出，保持 gitignore。人类可读的测试运行摘要放在
`docs/testing/results/`。

## Seed 策略

E2E 固定数据直接写入 `learned_paths`。

- 不通过 autonomous run 创建 LearnedPath。
- 不调用 `/exploration/autonomous-runs`。
- 不依赖 LLM 服务。
- 使用 `dedup_key` 前缀 `e2e:replay:`，方便清理且不影响其他数据。
- 外部 fixture provider 先生成 `apps/e2e/.tmp/replay-fixture-input.json`
  或通过 `E2E_REPLAY_FIXTURE_INPUT` 指定 manifest 路径。
- 生成的 fixture ID、target URL 和 mismatch URL 写入
  `apps/e2e/.tmp/replay-fixtures.json`。
- seed 脚本通过 API 侧 page analyzer 和 execution runtime 计算 manifest 中
  `target_url` 指向页面的签名。这是确定性页面分析，不是 autonomous run。

## 当前用例矩阵

| 用例 | 预期断言 |
| --- | --- |
| replay API 正常路径 | `status=succeeded`，`drift_status=none`，存在 step logs |
| catalog UI list | catalog 显示 seeded LearnedPath rows 和 trust labels |
| catalog UI trust filter | trust=flaky 过滤后仅显示 flaky seeded row |
| catalog UI drawer presence | actions drawer 显示 replay section、target URL input、disabled replay button、actions timeline |
| catalog UI replay path | drawer replay 结果展示成功且无 drift |
| `actions=[]` observational path | `status=observed`，steps 为空 |
| `page_mismatch` | `status=drifted`，`drift_status=page_mismatch` |
| `target_missing` | `status=drifted`，`drift_status=target_missing` |
| `unsupported_action` | `status=unsupported`，`drift_status=unsupported_action` |
| flaky warning | replay 请求成功，warnings 包含 flaky trust warning |
| deprecated 422 | replay 请求返回 HTTP 422 |
| signature changed but executable | `drift_status=signature_changed`，存在 warning，且 replay 仍可执行 |
| conversation runtime replay | session dispatch `/replay` 后完成，transcript/events 记录 replay 结果 |
| conversation CLI runtime replay | `wagent conversation` 创建 session、发送 `/replay`、读取 transcript/events |
| external fixture manifest ingestion | seed 脚本只读取外部 manifest，不内置页面路径、selector 或业务数据 |

## 暂缓项

- 真实 DOM 遮挡导致的 failed action。
- live autonomous learning 到 replay 的冒烟覆盖。
- multi-page workflow。
- task postcondition verification。

这些属于后续测试工作，不进入第一版确定性 E2E。
