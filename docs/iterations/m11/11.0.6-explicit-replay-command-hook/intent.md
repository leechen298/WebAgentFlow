# 11.0.6 Explicit Replay Command Hook

## 目标

将 M11.0 runtime conversation 中的显式
`/replay <learned_path_id> <url>` command 接入 M10 replay execution + drift
detection，使用户可以通过 conversation flow 触发一条已知 LearnedPath 的
确定性 replay，并在 conversation audit 中记录 replay requested / running /
completed / failed 证据。

## 动机

- M10 已完成 LearnedPath replay execution + drift detection。
- 11.0.5 已完成 service-only Orchestrator Dispatcher，但 `/replay` 目前只
  transition 到 `replay_requested`，不执行 side effect。
- 11.0.6 是第一个把 runtime conversation 和 M10 确定性能力连接起来的包。
- 这个连接必须是显式的：只能使用用户提供的 `learned_path_id + url`。
- 这不是 Agent D Path Planner，不做路径选择，不做任务理解，不做 slot
  binding。
- replay result 不是 `pass_gate`，不是 Supervisor verdict，只是 M10
  replay / drift result。
- 本包为 M11.0 runtime loop 提供一个 smoke hook，证明 conversation flow 能
  调用已完成的 deterministic engine capability。

## 边界（本轮不做）

- 不做 LearnedPath selection。
- 不做 natural-language task planning。
- 不做 slot binding。
- 不实现 Agent D / E / F / G / H。
- 不做 recovery / abort dialogue。
- 不做 teaching mode。
- 不做 artifact lifecycle。
- 不做 risk gate。
- 不做 multi-page workflow。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不做 M11.1。
- 不创建 M11.1 详情目录。
- 不新增 full external CLI / Skill / Tool。
- 不改变 M10 replay contract。
- 不把 replay result 说成 `pass_gate` 或 Supervisor verdict。

## 成功标准

- `/replay <learned_path_id> <url>` 通过 orchestrator 触发 M10 replay。
- replay command 必须显式包含 `learned_path_id + url`。
- missing args / malformed replay command 不执行 replay。
- no path selection。
- no autonomous run。
- no LLM provider。
- dispatch response 包含 replay result summary。
- conversation events 记录 replay lifecycle。
- replay started / completed / failed evidence 可审计。
- dispatch endpoint 对 malformed replay 和 replay runtime / resource failure 的
  响应必须可审计。
- public response 不暴露 `engine_command`。
- replay lifecycle 通过 events 记录，不写 session metadata。
- CLI 可以通过已有 `wagent conversation send <session_id> --content
  "/replay ..."` 触发 replay hook，具体路径在 `plan.md` 中明确。
- tests 覆盖 success / observed / drifted / unsupported / runtime error or
  failed / deprecated or missing path。
- 不破坏现有 conversation API / CLI tests。
