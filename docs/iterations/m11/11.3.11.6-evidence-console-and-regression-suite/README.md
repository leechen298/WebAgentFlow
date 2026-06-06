# 11.3.11.6 Evidence Console and Regression Suite

状态：PACKAGE_COMPLETE

## 摘要

本子包把 11.3.11 的 terminal evidence / attempt ingest evidence 暴露到 operator-facing
history detail，并用非 live 回归证明 API/detail payload 与 Console detail 能读取这些字段。

## Parent / Child

- Parent：`11.3.11-terminal-state-agent-learning-stop-control`
- Previous child：`11.3.11.5-attempt-evaluation-ingest-gate`
- Next：parent campaign closeout

## 范围

- Allowed：run detail read-model tests、Console detail evidence summary、component regression、docs closeout。
- Forbidden：live autonomous validation、new run trigger、direct autonomous endpoint calls、raw event/body display、
  LearnedPath ingest semantic changes。
