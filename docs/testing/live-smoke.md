# 手动 Live Smoke

本文件定义 release-only manual live smoke 流程。它不是 deterministic E2E，
不进入常规 CI。

## 适用范围

只有当需要验证 L1 live autonomous loop 时，才使用 `verify-scenario` skill。
普通 API / CLI / replay / conversation 回归测试不得通过 live autonomous run 完成。

## 硬边界

- 不直接 `curl` / `fetch` / `httpx` 调用 `/exploration/autonomous-runs`。
- 不直接调用 `/exploration/autonomous-runs/stream`。
- 不 import / run autonomous explorer。
- 不把 live smoke 标成 deterministic E2E。
- 不把 LLM-dependent result 标成 CI-safe。
- 如果由 AI Agent 代为执行，不允许用直接 API / 一次性脚本冒充 live smoke。
  必须保留 skill/CLI/UI 操作入口和原始输出记录。

## 执行方式

只能通过项目提供的 `verify-scenario` skill 执行，例如：

```bash
wagent verify --spec-id <spec_id> --scenario <scenario_id>
```

## 报告要求

真正执行 live smoke 时，报告必须写入：

```text
docs/testing/results/YYYY-MM-DD-verify-scenario-live-smoke.md
docs/testing/results/verify-scenario-live-smoke-latest.md
```

报告必须包含：

- command
- exit code
- raw stdout/stderr excerpt
- operator action log（谁用哪个入口触发、cwd、开始 / 结束时间）
- `pass_gate.status`
- `pass_gate.reasons`
- Supervisor verdict
- five scorecard scores
- Supervisor summary
- run_id
- LLM provider availability

`pass_gate.status=unverified` 不是 PASS。没有 Supervisor verdict / scorecard /
run_id 的结果不能写 PASS。

## 当前状态

当前未执行 live smoke。本文件只定义 manual release smoke runbook。
