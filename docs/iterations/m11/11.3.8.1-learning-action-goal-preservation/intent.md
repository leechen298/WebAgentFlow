# 意图（Intent）

状态：ready for review

## Problem / Purpose

PV-CLI-002 / PV-CLI-003 证明，WAgent 在外部黑盒页面上能完成学习流程，但学习完成后
session learned action metadata 只留下 `Learn how to create` 这类教学包装句式。
执行阶段的 intake 仍能识别 `Create inventory item` / `create_inventory_item`，但 runtime
没有可匹配的业务目标，因此拒绝执行。

本包的目标是把学习阶段已经识别出的业务动作保存为可复用 action identity，而不是只保存
教学句式。

## Why Now

11.3.7 first-wave behavior eval 已经通过，但外部黑盒验证在 2026-05-25 暴露出
learn-then-execute 的关键缺口。11.3.8 父包将修复拆为五个 child packages；本包是第一步，
必须先稳定 learned action metadata，后续 reusable utterances 和 matcher 才有可靠输入。

## Relationship To Roadmap / Milestone

- 属于 M11.3 post-closeout recovery follow-up。
- 不重写 M11 final closeout，也不把 M11 升级为完整 full learn-then-execute。
- 保持 L3 runtime conversation / task execution 范围，不新增 Agent role。
- 承接 `11.3.8-external-black-box-validation-recovery` 父包，交给 11.3.8.2 / 11.3.8.3。

## Non-goals

- 不修 action matcher；安全匹配属于 `11.3.8.3`。
- 不重新设计 suggested utterance；reusable utterance generation 属于 `11.3.8.2`。
- 不运行或更新外部黑盒验证结果；revalidation 属于 `11.3.8.5`。
- 不硬编码 `inventory item`、`5177/inventory`、外部站点 selector、seed data、field label 或 button text。
- 不新增 DB migration、public route、frontend UI、fixture page 或 autonomous-run flow。

## Success Criteria

- 设计明确 learned action metadata 中保留哪些业务身份字段，以及这些字段如何从 intake / learning request 进入 session metadata。
- 设计明确旧 session action 只含 `alias` / `utterances` 时仍兼容。
- 计划中的 focused tests 能证明 English learn input with business object 不再只保存 `Learn how to create`。
- 文档明确本包不声明 PV-CLI-003 fixed，也不声明外部 black-box validation passed。

## Expected Handoff

`11.3.8.2-suggested-utterance-generation` 可以读取本包定义和实现的 preserved business identity
来生成可复用 utterances。如果本包不能稳定 metadata shape，11.3.8.2 必须保持 blocked。

