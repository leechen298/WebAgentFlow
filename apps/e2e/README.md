# WebAgentFlow E2E

本 workspace 存放 WebAgentFlow 的确定性 Playwright Test E2E 覆盖。
当前套件覆盖 M10.2 LearnedPath replay API / catalog UI，以及 M11.0
conversation runtime replay smoke / CLI-driven replay smoke。

它不依赖 LLM 服务，不调用 autonomous-run 接口，也不创建 live autonomous run。

`apps/e2e/tests/` 下的测试按产品能力域组织。Replay 覆盖放在
`apps/e2e/tests/replay/`，conversation 覆盖放在
`apps/e2e/tests/conversation/`。这些是跨 console、API、数据库、
validation-site 和后端 Playwright replay 的 E2E 测试，不是
`apps/console/src/__tests__/` 下的 console 单元测试。
Conversation E2E 同时覆盖 API-request runtime flow 和真实 `wagent conversation`
CLI subprocess flow。

## 一次性设置

安装 workspace 依赖和 Playwright Test Chromium 浏览器：

```bash
pnpm install
pnpm run test:e2e:install
```

`pnpm run test:e2e:install` 会为 Playwright Test 安装 Chromium。
如果它在浏览器下载阶段卡住，可以稍后重试。如果本机已有浏览器缓存，
确定性 E2E 套件仍可能正常运行。

Replay API 本身使用 Python Playwright runtime。如果 API 环境里还没有安装
对应浏览器，也需要运行：

```bash
.venv/bin/python -m playwright install chromium
```

## 启动依赖

启动基础设施并执行迁移：

```bash
pnpm run docker:up
pnpm run db:migrate:api
```

分别在三个终端启动应用服务：

```bash
API_PORT=8001 pnpm run dev:api
pnpm run dev:validation
VITE_USE_DEV_PROXY=true API_PORT=8001 CONSOLE_PORT=5174 pnpm run dev:console
```

第一版 E2E 默认这些服务已经运行，不使用 Playwright `webServer` 自动编排。

## 写入 Replay 固定数据

写入确定性 LearnedPath 固定数据：

```bash
.venv/bin/python apps/e2e/scripts/seed-replay-fixtures.py
```

seed 脚本会：

- 只删除 `dedup_key` 以 `e2e:replay:` 开头的行。
- 插入固定 LearnedPath replay 数据。
- 将生成的 ID 写入 `apps/e2e/.tmp/replay-fixtures.json`。
- 使用 API 侧 page analyzer 计算当前 `/users` 签名。
- 不调用 `/exploration/autonomous-runs`。

需要清理 E2E 数据时运行：

```bash
.venv/bin/python apps/e2e/scripts/reset-e2e-db.py
```

## 运行 E2E

```bash
pnpm run test:e2e
pnpm run test:e2e:headed
pnpm run test:e2e:ui
```

默认服务地址：

- API：`http://127.0.0.1:8001`
- Console：`http://127.0.0.1:5174`
- Validation site：`http://127.0.0.1:5175`

可以通过环境变量覆盖：

```bash
E2E_API_BASE_URL=http://127.0.0.1:8001 \
E2E_CONSOLE_BASE_URL=http://127.0.0.1:5174 \
E2E_VALIDATION_BASE_URL=http://127.0.0.1:5175 \
pnpm run test:e2e
```

## Trace 输出

首次 retry 时会启用 trace。失败后可查看：

```bash
pnpm --filter @web-agent-flow/e2e exec playwright show-report
```

Playwright 原始输出保存在 gitignored 路径：

- `apps/e2e/test-results/`
- `apps/e2e/playwright-report/`

人类可读的测试运行摘要放在 `docs/testing/results/`。
