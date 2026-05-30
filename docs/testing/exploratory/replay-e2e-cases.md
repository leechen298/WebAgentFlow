# M10.2 Replay E2E 探索式用例矩阵

本矩阵只针对 M10.2 LearnedPath replay execution + drift detection。
它不是 WebAgentFlow 全项目测试矩阵。

每个 case 的报告必须包含：

- case id（用例编号）
- 目标
- 执行方法
- 预期证据
- PASS 条件
- 禁止捷径

## A. Preflight / 环境证据

### CASE PRE-001: API health

- 目标：确认 API 和 database 可用。
- 执行方法：实际请求 API health endpoint。
- 预期证据：命令、退出码、HTTP status、响应体摘录。
- PASS 条件：返回 HTTP 200，响应中包含 `code=0` 和 `database=ok`。
- 禁止捷径：没有命令输出不得 PASS。

### CASE PRE-002: fixture json exists

- 目标：确认 seed 已经生成 fixture id。
- 执行方法：读取 `apps/e2e/.tmp/replay-fixtures.json`。
- 预期证据：命令、退出码、JSON keys 摘录。
- PASS 条件：JSON 存在，包含 8 个 fixtures：`happy`、`observational`、
  `pageMismatch`、`targetMissing`、`unsupportedAction`、`flaky`、`deprecated`、
  `signatureChanged`。
- 禁止捷径：如果文件不存在，必须标记 `BLOCKED`，并提示从外部 Fixture-Site
  显式运行 local-only seed helper。该 raw 文件不是 provider redacted summary。

### CASE PRE-003: no autonomous endpoint in E2E source

- 目标：确认 E2E 不调用 autonomous run。
- 执行方法：搜索 `apps/e2e/` 中 `/exploration/autonomous-runs` 和
  `/exploration/autonomous-runs/stream` 的出现位置。
- 预期证据：搜索命令、退出码、输出摘录、判断理由。
- PASS 条件：如果出现这些字符串，只能出现在禁止请求保护逻辑、文档说明或边界说明中；
  不能作为请求目标、API helper 或真实调用路径。
- 禁止捷径：不能简单 grep 到字符串就判 FAIL，也不能不看用途就写 PASS。

## B. Deterministic E2E rerun / 固定回归复跑

### CASE E2E-001: run full deterministic E2E

- 目标：复跑 M10.2 replay deterministic E2E。
- 执行方法：运行 `pnpm run test:e2e`。
- 预期证据：命令、退出码、Playwright 输出摘录。
- PASS 条件：命令退出码 0，输出包含 `9 passed`。
- 禁止捷径：没有实际运行命令必须标记 `NOT_RUN`。服务未启动导致失败时，
  标记 `BLOCKED` 或 `FAIL`，并记录原始错误。

## C. Replay API exploratory / 直接 API 探索

### CASE API-001: happy path explicit replay

- 目标：验证显式 happy path replay。
- 执行方法：从 fixture JSON 读取 `happy` id，POST
  `/exploration/learned-paths/{id}/replay`，body 为
  `{ "url": "<fixture-provider>/records" }`。
- 预期证据：命令、退出码、HTTP status、响应关键字段。
- PASS 条件：HTTP 200，`code=0`，`status=succeeded`，
  `drift_status=none`，`steps.length > 0`。
- 禁止捷径：不得只引用 deterministic E2E 结果代替直接 API 探索。

### CASE API-002: missing URL request body

- 目标：验证 request validation。
- 执行方法：用 `happy` id 请求 replay，但 body 为空对象 `{}`。
- 预期证据：命令、退出码、HTTP status。
- PASS 条件：HTTP 422。
- 禁止捷径：不得把 422 写成失败，它是预期行为。

### CASE API-003: nonexistent path id

- 目标：验证显式 path replay 的不存在路径语义。
- 执行方法：请求不存在的 UUID，例如
  `00000000-0000-0000-0000-000000000000`。
- 预期证据：命令、退出码、HTTP status。
- PASS 条件：HTTP 404。
- 禁止捷径：不得把它解释成 `candidate_not_found`；本 endpoint 应返回 HTTP 404。

### CASE API-004: signature changed with query

- 目标：确认 query signature drift 可执行。
- 执行方法：`happy` id replay `<fixture-provider>/records?name=alice`。
- 预期证据：命令、退出码、HTTP status、响应关键字段。
- PASS 条件：HTTP 200，`status=succeeded` 或 `observed`，
  `drift_status=signature_changed`，warnings 非空。
- 禁止捷径：不得只检查 HTTP 200；必须检查 drift status 和 warnings。

### CASE API-005: deprecated path blocked

- 目标：确认 deprecated path 不执行。
- 执行方法：`deprecated` id replay `<fixture-provider>/records`。
- 预期证据：命令、退出码、HTTP status。
- PASS 条件：HTTP 422。
- 禁止捷径：不得把 422 写成失败，它是预期行为。

### CASE API-006: unsupported action remains structured

- 目标：确认 unsupported action 返回结构化 replay 结果，不是 500。
- 执行方法：`unsupportedAction` id replay `<fixture-provider>/records`。
- 预期证据：命令、退出码、HTTP status、响应关键字段。
- PASS 条件：HTTP 200，`status=unsupported`，
  `drift_status=unsupported_action`。
- 禁止捷径：不得只检查没有崩溃；必须检查 replay status。

## D. Catalog UI exploratory / UI 探索

本组 case 的 PASS 必须来自 Agent-operated UI exploratory 证据：Codex、Claude Code
或其他具备浏览器能力的 Agent，或 headed Playwright，打开真实页面，执行可见 UI 操作，
并记录页面观察、截图、trace、video 或明确 browser observation。Headless E2E 只能作为
deterministic E2E 证据；API-only 调用不能作为本组 PASS 证据。

### CASE UI-001: replay button disabled on empty URL

- 目标：确认空 URL 时不能触发 replay。
- 执行方法：打开 LearnedPath catalog，打开 happy path drawer，不输入 URL。
- 预期证据：Agent-operated browser / headed Playwright 的可见页面
  操作记录、截图/trace/video 或 browser observation 摘录。
- PASS 条件：Replay 按钮 disabled。
- 禁止捷径：不得只读代码推断。

### CASE UI-002: happy replay renders result

- 目标：确认 catalog UI 展示 happy replay 结果。
- 执行方法：打开 happy path drawer，输入 `<fixture-provider>/records`，点击 Replay。
- 预期证据：Agent-operated browser / headed Playwright 的可见页面
  操作记录、截图/trace/video 或 browser observation 摘录。
- PASS 条件：UI 展示 `Succeeded`、`No drift`、final URL 或 step log；
  同时没有请求 `/exploration/autonomous-runs` 或 stream。
- 禁止捷径：不得只调用 API 代替 UI 操作；不得把 headless E2E 的 PASS 直接写成
  Agent-operated UI PASS。

### CASE UI-003: flaky replay warning renders

- 目标：确认 flaky/trust warning 在 UI 中可见。
- 执行方法：打开 flaky path drawer，输入 `<fixture-provider>/records`，点击 Replay。
- 预期证据：Agent-operated browser / headed Playwright 的可见页面
  操作记录、截图/trace/video 或 browser observation 摘录。
- PASS 条件：UI 展示 replay 结果，并展示 flaky/trust warning。
- 禁止捷径：如果文案定位失败但 API 有 warning，不得写 PASS；应写 FAIL 或
  BLOCKED，并说明 UI 定位问题。

### CASE UI-004: target missing drift renders

- 目标：确认 target missing drift 在 UI 中可见。
- 执行方法：打开 targetMissing path drawer，输入 `<fixture-provider>/records`，点击 Replay。
- 预期证据：Agent-operated browser / headed Playwright 的可见页面
  操作记录、截图/trace/video 或 browser observation 摘录。
- PASS 条件：UI 展示 `drifted` / `target_missing` 或 drift reason。
- 禁止捷径：必须实际操作 UI，不得只调用 API。

### CASE UI-005: deprecated replay error renders

- 目标：确认 deprecated replay 的 422 错误能在 UI 中展示。
- 执行方法：打开 deprecated path drawer，输入 `<fixture-provider>/records`，点击 Replay。
- 预期证据：Agent-operated browser / headed Playwright 的可见页面
  操作记录、截图/trace/video 或 browser observation 摘录。
- PASS 条件：UI 展示 error alert，错误来自 HTTP 422。
- 禁止捷径：必须实际操作 UI，不得只调用 API。

## E. Report discipline / 报告纪律

### CASE REP-001: evidence-only reporting

- 目标：确认本次报告没有无证据 PASS。
- 执行方法：检查本次报告。
- 预期证据：报告中的 case 记录、命令表、原始证据摘录。
- PASS 条件：每个 PASS 都附带命令、退出码、原始输出摘录；没跑的用例必须是
  `NOT_RUN` 或 `BLOCKED`。
- 禁止捷径：禁止出现无证据的“看起来正常”“应该通过”“我认为完成”。
