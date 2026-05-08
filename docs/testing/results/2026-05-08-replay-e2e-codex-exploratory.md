# M10.2 Replay E2E Codex 探索式验证报告

日期：2026-05-08

当前 commit：

```text
068c897a05a62cb32653d9ad84c51ce531709b15
```

工作区状态摘录：

```text
 M docs/testing/README.md
 M docs/testing/codex-exploratory.md
 M docs/testing/e2e.md
?? docs/testing/exploratory/
?? docs/testing/features/
?? docs/testing/results/2026-05-08-replay-e2e-codex-exploratory.md
```

执行者：Codex

范围：仅验证 M10.2 LearnedPath replay execution + drift detection 的 E2E 与
exploratory 边界；不是 WebAgentFlow 全项目测试。

## 摘要

- PASS：12
- FAIL：0
- BLOCKED：0
- NOT_RUN：4
- 是否调用 autonomous endpoints：no
- 是否使用 LLM provider：no

说明：在默认沙箱内，localhost 访问和 Chromium 启动出现权限相关失败；随后使用批准的
升级权限重跑关键验证，获得可用证据。报告中的 PASS 均以升级权限下的真实命令输出为准。

## 执行命令

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `git rev-parse HEAD` | 0 | 输出当前 commit |
| `git status --short` | 0 | 输出本轮文档变更 |
| `curl -sS -i http://127.0.0.1:8001/health` | 7 | 默认沙箱内无法连接 API |
| `curl -sS -i http://127.0.0.1:8001/health` | 0 | 升级权限后返回 HTTP 200，database ok |
| `python3 -m json.tool apps/e2e/.tmp/replay-fixtures.json` | 0 | fixture JSON 可读取，包含 8 个 fixtures |
| `rg -n "/exploration/autonomous-runs\|autonomous-runs/stream" apps/e2e` | 0 | 只命中文档说明和禁止请求保护逻辑 |
| `pnpm run test:e2e` | 1 | 默认沙箱内 localhost / Chromium 权限失败 |
| `pnpm run test:e2e` | 0 | 升级权限后 9 passed |
| `python3 - <<'PY' ... replay API exploratory ... PY` | 0 | 6 个 API exploratory case 均返回预期结构 |
| `git diff --check` | 0 | 通过，无输出 |

## 用例结果

### CASE PRE-001: API health

- 状态：PASS
- 命令或方法：`curl -sS -i http://127.0.0.1:8001/health`
- 退出码：0
- 证据摘录：

```text
HTTP/1.1 200 OK
{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}
```

- 备注：默认沙箱内首次运行同一命令退出 7，错误为 `Failed to connect to 127.0.0.1 port 8001`；升级权限后通过。
- 后续处理：无。

### CASE PRE-002: fixture json exists

- 状态：PASS
- 命令或方法：`python3 -m json.tool apps/e2e/.tmp/replay-fixtures.json`
- 退出码：0
- 证据摘录：

```text
"fixtures": {
  "happy": { "scenario": "e2e:replay:happy", "trust": "confirmed" },
  "observational": { "scenario": "e2e:replay:observational", "trust": "confirmed" },
  "pageMismatch": { "scenario": "e2e:replay:page-mismatch", "trust": "confirmed" },
  "targetMissing": { "scenario": "e2e:replay:target-missing", "trust": "confirmed" },
  "unsupportedAction": { "scenario": "e2e:replay:unsupported-action", "trust": "confirmed" },
  "flaky": { "scenario": "e2e:replay:flaky", "trust": "flaky" },
  "deprecated": { "scenario": "e2e:replay:deprecated", "trust": "deprecated" },
  "signatureChanged": { "scenario": "e2e:replay:signature-changed", "trust": "confirmed" }
}
```

- 备注：fixture JSON 已存在并包含 8 个 replay fixtures。
- 后续处理：无。

### CASE PRE-003: no autonomous endpoint in E2E source

- 状态：PASS
- 命令或方法：`rg -n "/exploration/autonomous-runs|autonomous-runs/stream" apps/e2e`
- 退出码：0
- 证据摘录：

```text
apps/e2e/README.md:66:- 不调用 `/exploration/autonomous-runs`。
apps/e2e/tests/replay/catalog-ui.spec.ts:17:      url.includes('/exploration/autonomous-runs') ||
apps/e2e/tests/replay/catalog-ui.spec.ts:18:      url.includes('/exploration/autonomous-runs/stream')
```

- 备注：命中项只有 README 边界说明，以及 catalog UI E2E 的禁止请求保护逻辑。没有发现作为请求目标、API helper 或真实调用路径的 autonomous endpoint。
- 后续处理：无。

### CASE E2E-001: run full deterministic E2E

- 状态：PASS
- 命令或方法：`pnpm run test:e2e`
- 退出码：0
- 证据摘录：

```text
Running 9 tests using 2 workers
✓ tests/replay/api.spec.ts:46 happy path succeeds with no drift
✓ tests/replay/api.spec.ts:56 observational path reports observed with no steps
✓ tests/replay/api.spec.ts:65 page mismatch blocks replay
✓ tests/replay/catalog-ui.spec.ts:12 LearnedPath catalog can replay a seeded happy path
✓ tests/replay/api.spec.ts:74 target missing blocks replay
✓ tests/replay/api.spec.ts:83 unsupported action reports unsupported action drift
✓ tests/replay/api.spec.ts:92 flaky path replays with trust warning
✓ tests/replay/api.spec.ts:100 deprecated path returns 422
✓ tests/replay/api.spec.ts:107 signature changed remains executable when targets still match
9 passed (13.7s)
```

- 备注：默认沙箱内首次运行退出 1，错误包含 `connect EPERM 127.0.0.1:8001` 和 Chromium Mach permission；升级权限后通过。
- 后续处理：无。

### CASE API-001: happy path explicit replay

- 状态：PASS
- 命令或方法：Python stdlib `urllib` 读取 fixture JSON 后 POST replay API。
- 退出码：0
- 证据摘录：

```text
{"case_id": "API-001", "code": 0, "drift_status": "none", "http_status": 200, "msg": "ok", "status": "succeeded", "steps_length": 2, "warnings_count": 0}
```

- 备注：HTTP 200，`code=0`，`status=succeeded`，`drift_status=none`，steps 非空。
- 后续处理：无。

### CASE API-002: missing URL request body

- 状态：PASS
- 命令或方法：Python stdlib `urllib` 用 happy id POST replay API，body 为 `{}`。
- 退出码：0
- 证据摘录：

```text
{"case_id": "API-002", "code": 422, "drift_status": null, "http_status": 422, "msg": "url: Field required", "status": null, "steps_length": null, "warnings_count": null}
```

- 备注：HTTP 422 是预期 request validation 行为。
- 后续处理：无。

### CASE API-003: nonexistent path id

- 状态：PASS
- 命令或方法：Python stdlib `urllib` 请求
  `00000000-0000-0000-0000-000000000000`。
- 退出码：0
- 证据摘录：

```text
{"case_id": "API-003", "code": 404, "drift_status": null, "http_status": 404, "msg": "learned_path not found: 00000000-0000-0000-0000-000000000000", "status": null, "steps_length": null, "warnings_count": null}
```

- 备注：显式 path replay 对不存在 id 返回 HTTP 404，没有返回 `candidate_not_found`。
- 后续处理：无。

### CASE API-004: signature changed with query

- 状态：PASS
- 命令或方法：Python stdlib `urllib` 用 happy id replay
  `http://127.0.0.1:5175/users?name=alice`。
- 退出码：0
- 证据摘录：

```text
{"case_id": "API-004", "code": 0, "drift_status": "signature_changed", "http_status": 200, "msg": "ok", "status": "succeeded", "steps_length": 2, "warnings_count": 1}
```

- 备注：query signature drift 非阻断，仍可执行。
- 后续处理：无。

### CASE API-005: deprecated path blocked

- 状态：PASS
- 命令或方法：Python stdlib `urllib` 用 deprecated id replay `/users`。
- 退出码：0
- 证据摘录：

```text
{"case_id": "API-005", "code": 422, "drift_status": null, "http_status": 422, "msg": "learned_path is deprecated", "status": null, "steps_length": null, "warnings_count": null}
```

- 备注：HTTP 422 是预期行为，deprecated path 不执行。
- 后续处理：无。

### CASE API-006: unsupported action remains structured

- 状态：PASS
- 命令或方法：Python stdlib `urllib` 用 unsupportedAction id replay `/users`。
- 退出码：0
- 证据摘录：

```text
{"case_id": "API-006", "code": 0, "drift_status": "unsupported_action", "http_status": 200, "msg": "ok", "status": "unsupported", "steps_length": 0, "warnings_count": 0}
```

- 备注：HTTP 200，返回结构化 `status=unsupported` 和 `drift_status=unsupported_action`，不是 500。
- 后续处理：无。

### CASE UI-001: replay button disabled on empty URL

- 状态：NOT_RUN
- 命令或方法：未执行。
- 退出码：不适用。
- 证据摘录：无。
- 备注：本轮不修改产品 UI、不添加 `data-testid`、不修改 E2E spec；该专项 UI exploratory 未另写临时浏览器脚本。
- 后续处理：如后续要覆盖，可新增长期 Playwright E2E case 或明确允许临时 UI exploratory 脚本。

### CASE UI-002: happy replay renders result

- 状态：PASS
- 命令或方法：`pnpm run test:e2e` 中的 catalog UI E2E。
- 退出码：0
- 证据摘录：

```text
✓ tests/replay/catalog-ui.spec.ts:12 LearnedPath catalog can replay a seeded happy path (5.4s)
```

- 备注：该 deterministic UI E2E 实际打开 catalog、打开 happy path drawer、输入 `/users`、点击 Replay，并断言 `Succeeded`、`No drift`、final URL 和 `Step 0`；同一 spec 内监听 forbidden requests。
- 后续处理：无。

### CASE UI-003: flaky replay warning renders

- 状态：NOT_RUN
- 命令或方法：未执行。
- 退出码：不适用。
- 证据摘录：无。
- 备注：本轮不修改 E2E spec，也不新增临时 UI exploratory 脚本。
- 后续处理：如该 UI warning 成为关键验收点，补入 `apps/e2e/tests/replay/` 的长期 E2E。

### CASE UI-004: target missing drift renders

- 状态：NOT_RUN
- 命令或方法：未执行。
- 退出码：不适用。
- 证据摘录：无。
- 备注：本轮不修改 E2E spec，也不新增临时 UI exploratory 脚本。
- 后续处理：如该 UI drift 展示成为关键验收点，补入 `apps/e2e/tests/replay/` 的长期 E2E。

### CASE UI-005: deprecated replay error renders

- 状态：NOT_RUN
- 命令或方法：未执行。
- 退出码：不适用。
- 证据摘录：无。
- 备注：本轮不修改 E2E spec，也不新增临时 UI exploratory 脚本。
- 后续处理：如该 UI error 展示成为关键验收点，补入 `apps/e2e/tests/replay/` 的长期 E2E。

### CASE REP-001: evidence-only reporting

- 状态：PASS
- 命令或方法：检查本报告的 case 记录和命令证据。
- 退出码：不适用。
- 证据摘录：

```text
每个 PASS case 均包含命令或方法、退出码或不适用说明、证据摘录。
未执行的 UI-001、UI-003、UI-004、UI-005 均标记 NOT_RUN。
```

- 备注：报告没有把未执行 case 写成 PASS。
- 后续处理：无。

## 原始证据附录

### 默认沙箱内 API health 失败

```text
curl: (7) Failed to connect to 127.0.0.1 port 8001 after 0 ms: Couldn't connect to server
```

### 默认沙箱内 E2E 失败摘录

```text
Error: apiRequestContext.post: connect EPERM 127.0.0.1:8001 - Local (0.0.0.0:0)
...
FATAL:base/apple/mach_port_rendezvous_mac.cc:159
bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer... Permission denied (1100)
...
9 failed
```

### 升级权限后 E2E 通过摘录

```text
Running 9 tests using 2 workers
9 passed (13.7s)
```

### API exploratory 输出

```text
{"case_id": "API-001", "code": 0, "drift_status": "none", "http_status": 200, "msg": "ok", "status": "succeeded", "steps_length": 2, "warnings_count": 0}
{"case_id": "API-002", "code": 422, "drift_status": null, "http_status": 422, "msg": "url: Field required", "status": null, "steps_length": null, "warnings_count": null}
{"case_id": "API-003", "code": 404, "drift_status": null, "http_status": 404, "msg": "learned_path not found: 00000000-0000-0000-0000-000000000000", "status": null, "steps_length": null, "warnings_count": null}
{"case_id": "API-004", "code": 0, "drift_status": "signature_changed", "http_status": 200, "msg": "ok", "status": "succeeded", "steps_length": 2, "warnings_count": 1}
{"case_id": "API-005", "code": 422, "drift_status": null, "http_status": 422, "msg": "learned_path is deprecated", "status": null, "steps_length": null, "warnings_count": null}
{"case_id": "API-006", "code": 0, "drift_status": "unsupported_action", "http_status": 200, "msg": "ok", "status": "unsupported", "steps_length": 0, "warnings_count": 0}
```

## 最终声明

本报告只在包含证据时将 case 标记为 PASS。没有执行的 case 标记为 NOT_RUN 或 BLOCKED。
