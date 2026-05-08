# 确定性 E2E

WebAgentFlow 使用 Playwright Test 做浏览器 E2E 和 API request 验证。
E2E workspace 位于 `apps/e2e/`。

E2E 用例按产品能力域组织在 `apps/e2e/tests/` 下，例如
`apps/e2e/tests/replay/`。这些用例是跨 console、API、数据库、
validation-site 和后端 Playwright replay 的产品闭环测试。
它们不是 console 前端单元测试，不应放到 `apps/console/src/__tests__/`。

## 第一阶段目标

第一阶段 E2E 覆盖已经完成的 M10.2 replay 能力：

- LearnedPath replay API。
- LearnedPath catalog UI replay 区块。

这不会新增产品行为，也不会扩大 M10.2 范围。

Replay 测试域的长期矩阵见 [features/replay.md](./features/replay.md)。
Codex 探索式补充用例见
[exploratory/replay-e2e-cases.md](./exploratory/replay-e2e-cases.md)。

## 环境组成

第一版默认由开发者手动启动依赖服务：

- FastAPI server。
- validation-site。
- console。
- 已完成 schema 迁移并写入 E2E seed 数据的 PostgreSQL。

Playwright config 暂时不使用 `webServer` 编排全部服务。等回归轨道稳定后，
后续再考虑自动编排。

按以下顺序运行确定性 E2E：

1. 启动 Docker 基础设施：`pnpm run docker:up`。
2. 执行 API 数据库迁移：`pnpm run db:migrate:api`。
3. 启动 API server：`API_PORT=8001 pnpm run dev:api`。
4. 启动 validation-site：`pnpm run dev:validation`。
5. 启动 console：
   `VITE_USE_DEV_PROXY=true API_PORT=8001 CONSOLE_PORT=5174 pnpm run dev:console`。
6. 写入 replay 固定数据：
   `.venv/bin/python apps/e2e/scripts/seed-replay-fixtures.py`。
7. 运行 E2E：`pnpm run test:e2e`。

首次运行前，用 `pnpm run test:e2e:install` 安装 Playwright Test Chromium
浏览器。如果该命令卡在 `playwright install chromium`，通常是浏览器下载或网络
环境问题。可以稍后重试；如果本机已经有 Chromium 缓存，确定性 E2E 仍可能正常运行。

查看 [results/2026-05-08-replay-e2e-first-run.md](./results/2026-05-08-replay-e2e-first-run.md)
了解 M10.2 replay E2E 首次实跑结果，以及当次观察到的浏览器安装注意事项。

`apps/e2e/test-results/` 和 `apps/e2e/playwright-report/` 是 Playwright
原始输出，保持 gitignore。人类可读的测试运行摘要放在
`docs/testing/results/`。

## Seed 策略

E2E 固定数据直接写入 `learned_paths`。

- 不通过 autonomous run 创建 LearnedPath。
- 不调用 `/exploration/autonomous-runs`。
- 不依赖 LLM 服务。
- 使用 `dedup_key` 前缀 `e2e:replay:`，方便清理且不影响其他数据。
- 生成的 fixture ID 写入 `apps/e2e/.tmp/replay-fixtures.json`。

seed 脚本通过 API 侧 page analyzer 和 execution runtime 计算当前 `/users`
页面签名。这是确定性页面分析，不是 autonomous run。

## 第一批用例矩阵

| 用例                             | 预期断言                                                               |
| -------------------------------- | ---------------------------------------------------------------------- |
| replay API 正常路径              | `status=succeeded`，`drift_status=none`，存在 step logs                |
| catalog UI 正常路径              | drawer replay 结果展示成功且无 drift                                   |
| `actions=[]` observational path  | `status=observed`，steps 为空                                          |
| `page_mismatch`                  | `status=drifted`，`drift_status=page_mismatch`                         |
| `target_missing`                 | `status=drifted`，`drift_status=target_missing`                        |
| `unsupported_action`             | `status=unsupported`，`drift_status=unsupported_action`                |
| flaky warning                    | replay 请求成功，warnings 包含 flaky trust warning                     |
| deprecated 422                   | replay 请求返回 HTTP 422                                               |
| signature changed but executable | `drift_status=signature_changed`，存在 warning，且 replay 仍可执行     |

## 暂缓项

- 真实 DOM 遮挡导致的 failed action。
- live autonomous learning 到 replay 的冒烟覆盖。
- multi-page workflow。
- task postcondition verification。

这些属于后续测试工作，不进入第一版确定性 E2E。
