# M10.2 Replay Visual UI Exploratory 验证报告

日期：2026-05-09

范围：M10.2 LearnedPath replay execution + drift detection 的 visual UI
exploratory validation。该报告只覆盖 replay 测试域，不是 WebAgentFlow 全项目
测试。

证据类型：Codex Browser panel / in-app browser 可视化操作。不是 headless E2E，
也不是 API-only exploratory。

## 摘要

- PASS：9
- FAIL：0
- BLOCKED：0
- NOT_RUN：0
- 是否调用 autonomous endpoints：no
- 是否使用 LLM provider：no

本次验证打开 console 的 LearnedPath catalog 页面，逐个打开 seeded LearnedPath 的
drawer，填写目标 URL，点击“重跑”，并观察页面中可见的 replay 结果。

## 当前上下文

当前 commit：

```text
23b3f21 docs(iterations): update 11.0.3 review status to implemented
```

本次 visual UI 验证本身未产生产品代码、E2E spec、package scripts 或
`docs/iterations` 改动。本报告写入后，工作区变更限定在 `docs/testing/**`。

```text
 M docs/testing/README.md
 M docs/testing/codex-exploratory.md
 M docs/testing/e2e.md
 M docs/testing/exploratory/README.md
 M docs/testing/exploratory/replay-e2e-cases.md
 M docs/testing/exploratory/replay-e2e-run-prompt.md
 M docs/testing/features/replay.md
?? docs/testing/exploratory/replay-visual-ui-run-prompt.md
?? docs/testing/results/2026-05-09-replay-visual-ui-exploratory.md
```

## 前置检查

### API health

命令：

```bash
curl -i http://127.0.0.1:8001/health
```

结果摘录：

```text
HTTP/1.1 200 OK
{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}
```

### console / fixture-site

默认沙箱内直接访问 `5174` / `5175` 曾返回连接失败；确认已有本机 Node 进程监听后，
升级权限访问通过：

```text
http://127.0.0.1:5174/exploration/learned-paths -> HTTP/1.1 200 OK
https://example.invalid/records -> HTTP/1.1 200 OK
```

### E2E seed

默认沙箱运行 seed 时，Python Playwright Chromium 因 macOS MachPort 权限失败。
升级权限后运行成功：

```bash
.venv/bin/python apps/e2e/scripts/seed-replay-fixtures.py
```

成功写入 8 个 fixtures：

```text
happy
observational
pageMismatch
targetMissing
unsupportedAction
flaky
deprecated
signatureChanged
```

seed 输出写入：

```text
apps/e2e/.tmp/replay-fixtures.json
```

## Browser 操作方式

使用 Codex in-app browser 打开：

```text
http://127.0.0.1:5174/exploration/learned-paths
```

操作流程：

1. 在 LearnedPath catalog 中定位 `e2e:replay:*` seeded rows。
2. 对每个 scenario 点击“查看动作”打开 drawer。
3. 在 drawer 的“重跑这条路径”区域填写目标 URL。
4. 点击“重跑”。
5. 观察页面可见结果文本。

最终浏览器页面停留在 `e2e:replay:signature-changed` drawer，并可见：

```text
重跑状态：成功
页面变化：签名已变化
警告：Signature changed: query_signature or dom_fingerprint differs from stored values
最终 URL：https://example.invalid/records?name=alice
```

本次还通过 in-app browser 显示了该最终状态截图；截图未作为文件提交。

## Case 结果

| Case | Scenario | 操作 URL | 状态 | 页面可见证据 |
| --- | --- | --- | --- | --- |
| UI-001 | `e2e:replay:happy` | empty | PASS | “重跑”按钮 disabled |
| UI-002 | `e2e:replay:happy` | `https://example.invalid/records` | PASS | `成功`、`无变化`、最终 URL、`Step 0` |
| UI-OBS | `e2e:replay:observational` | `https://example.invalid/records` | PASS | `这条路径没有动作，已完成页面观察`、`无变化`、`暂无步骤日志` |
| UI-PAGE-MISMATCH | `e2e:replay:page-mismatch` | `https://example.invalid/entry` | PASS | `页面变化导致无法重跑`、`页面不匹配` |
| UI-004 | `e2e:replay:target-missing` | `https://example.invalid/records` | PASS | `页面变化导致无法重跑`、`找不到当初记录的按钮或输入框` |
| UI-UNSUPPORTED | `e2e:replay:unsupported-action` | `https://example.invalid/records` | PASS | `这类动作当前还不能重跑` |
| UI-003 | `e2e:replay:flaky` | `https://example.invalid/records` | PASS | `成功`、`Path trust is flaky` |
| UI-005 | `e2e:replay:deprecated` | `https://example.invalid/records` | PASS | `重跑失败`、`learned_path is deprecated` |
| UI-SIGNATURE | `e2e:replay:signature-changed` | `https://example.invalid/records` | PASS | `成功`、`签名已变化` |

## 原始 browser observation 摘录

本次浏览器操作返回的 case 结果摘录：

```json
[
  {
    "id": "UI-001",
    "scenario": "e2e:replay:happy",
    "status": "PASS",
    "checks": {
      "empty URL replay button disabled": true
    }
  },
  {
    "id": "UI-002",
    "scenario": "e2e:replay:happy",
    "url": "https://example.invalid/records",
    "status": "PASS",
    "checks": {
      "成功": true,
      "无变化": true,
      "https://example.invalid/records": true,
      "Step 0": true
    }
  },
  {
    "id": "UI-OBS",
    "scenario": "e2e:replay:observational",
    "url": "https://example.invalid/records",
    "status": "PASS",
    "checks": {
      "这条路径没有动作，已完成页面观察": true,
      "无变化": true,
      "暂无步骤日志": true
    }
  },
  {
    "id": "UI-PAGE-MISMATCH",
    "scenario": "e2e:replay:page-mismatch",
    "url": "https://example.invalid/entry",
    "status": "PASS",
    "checks": {
      "页面变化导致无法重跑": true,
      "页面不匹配": true
    }
  },
  {
    "id": "UI-004",
    "scenario": "e2e:replay:target-missing",
    "url": "https://example.invalid/records",
    "status": "PASS",
    "checks": {
      "页面变化导致无法重跑": true,
      "找不到当初记录的按钮或输入框": true
    }
  },
  {
    "id": "UI-UNSUPPORTED",
    "scenario": "e2e:replay:unsupported-action",
    "url": "https://example.invalid/records",
    "status": "PASS",
    "checks": {
      "这类动作当前还不能重跑": true
    }
  },
  {
    "id": "UI-003",
    "scenario": "e2e:replay:flaky",
    "url": "https://example.invalid/records",
    "status": "PASS",
    "checks": {
      "成功": true,
      "Path trust is flaky": true
    }
  },
  {
    "id": "UI-005",
    "scenario": "e2e:replay:deprecated",
    "url": "https://example.invalid/records",
    "status": "PASS",
    "checks": {
      "重跑失败": true,
      "learned_path is deprecated": true
    }
  },
  {
    "id": "UI-SIGNATURE",
    "scenario": "e2e:replay:signature-changed",
    "url": "https://example.invalid/records",
    "status": "PASS",
    "checks": {
      "成功": true,
      "签名已变化": true
    }
  }
]
```

## 边界确认

- 没有调用 `/exploration/autonomous-runs`。
- 没有调用 `/exploration/autonomous-runs/stream`。
- 没有依赖 LLM provider。
- 没有修改产品代码。
- 没有修改 E2E spec。
- 没有修改 package scripts。
- 没有新增 `data-testid`。
- 没有把 headless E2E 或 API-only response 写成 visual UI PASS。

## 检查结果

```text
git diff --check
```

结果：通过，无输出。
