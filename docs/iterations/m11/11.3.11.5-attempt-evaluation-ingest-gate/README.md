# 11.3.11.5 Attempt Evaluation Ingest Gate

状态：PACKAGE_COMPLETE

## 摘要

本子包把 child 4 的 `TerminalStateVerdict` 接入 attempt-level evaluation / ingest eligibility
边界，但不把 terminal-state detection 本身当作成功。它定义 AttemptTerminalSummary、LearnedPath
候选资格、failed / unverified evidence 的保留规则和非 live 测试。

## Parent / Child

- Parent：`11.3.11-terminal-state-agent-learning-stop-control`
- Previous child：`11.3.11.4-terminal-state-agent-stop-control`
- Next child：`11.3.11.6-evidence-console-and-regression-suite`

## 边界

- Allowed：schema / pure service / learning ingest guard / non-live tests。
- Forbidden：live autonomous validation、Console UI、new DB migration、direct autonomous endpoint calls、把
  `terminal_unverified` 或 `terminal_failed` 沉淀为成功 LearnedPath。

## 当前门禁

Implementation is authorized for the scoped schema/service/ingest-gate/test changes recorded in `review.md`.
