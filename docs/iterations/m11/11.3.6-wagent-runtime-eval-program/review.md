# 复盘 / 评审（Review）

状态：draft_for_review（总体测试规划已生成，未实现代码）

## 2026-05-22 拆分规划

- Author：Codex
- Decision：docs_created
- Notes：
  - 用户判断 11.3.6 更适合作为总体测试规划，runner core 应下沉到 11.3.6.1。
  - 已将原 `11.3.6-wagent-runtime-eval-runner` 移动为
    `11.3.6.1-wagent-runtime-eval-runner-core`。
  - 新增 `11.3.6-wagent-runtime-eval-program` 作为 runtime eval 总纲。
  - 11.3.6.1 保留 ready-for-implementation 状态。
  - 后续 11.3.6.2 / 11.3.6.3 / 11.3.6.4 按 case family 独立开包。

## 设计评审

- Reviewer：pending
- Decision：pending
- Notes：
  - 等待用户复核拆分后的总纲和子包边界。

## 未运行项

| Item | Reason |
|---|---|
| pytest | docs-only split |
| ruff | no Python changed |
| eval runner | not implemented in this package |
| autonomous run | prohibited / out of scope |
| `verify-scenario` | out of scope |

## 后续事项

- 用户确认拆分后，可以从 11.3.6.1 开始实现 runner core。
- 11.3.6.2 之前需要先设计 failure recovery 的稳定 fault injection / eval-only hook。
