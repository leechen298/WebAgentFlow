# 意图（Intent）

状态：PACKAGE_COMPLETE

## 背景

Child 2-5 已经生成并保存 redacted browser event timeline、terminal-state verdict 和
attempt-ingest evaluation。Operator 需要在 run history/detail 看到终态证据和入库门禁结果，否则
失败 / unverified 的原因只能从 raw JSON 推断。

## 目标

- 在 Console run detail 提供 compact terminal / ingest evidence summary。
- 保持 raw JSON 作为完整审计出口。
- 用 API / component tests 验证 evidence 字段可读、legacy result 不崩。
- 完成 11.3.11 campaign 的非 live closeout。

## 非目标

- 不新增 API endpoint。
- 不展示 raw request/response body。
- 不运行 live autonomous validation。
- 不做 LearnedPath detail 新页面。
