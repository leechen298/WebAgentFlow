# 意图（Intent）

状态：ready_for_implementation（design review passed，未实现代码）

## 目标

修复 11.3.6.5 service-available closeout 中暴露的 pending choice / planner-backed choice required
gate failures，并补强 runner artifact redaction，使 11.3.6.3 和 11.3.6.4 eval 可以在服务可用时
以 exit `0` 通过。

## 动机

11.3.6.5 closeout 已经完成两轮验证：

- 第一轮因 API health 不可用返回 exit `2`，只说明环境 blocked。
- 第二轮 API `/health` 和 product `/items` 均可访问，两个 required eval 进入 Conversation API 后
  返回 exit `1`，说明存在真实功能 / redaction gate failure。

失败点明确：

- `pending_choice_multi_candidate`：`public_choice_payload_sanitized` failed，public surfaces 暴露了
  private pending choice token `learned_path_id`。
- `planner_backed_choice`：planner candidates / choices 创建成功，用户选择 A dispatch 成功，但没有
  `chat_execution_started`，execution / verification / final response gates failed。
- raw planner rerun output 含 full private path id，不能提交为证据。

这些问题已经超出 closeout 文档范围，必须用代码型 fix 迭代处理。

## 边界 / 非目标

- 不新增 runtime 能力；只修复已实现路径的 required gate failures。
- 不改变 product lifecycle stage、internal Agent role 或 M11 milestone boundary。
- 不新增 API endpoint、DB migration 或新的 package script。
- 不运行 autonomous-run endpoints，不调用 `verify-scenario`。
- 不把 blocked / failed artifact 改写成 pass；必须通过 rerun 得到新的 pass artifact。

## 成功标准

- `pnpm run eval:wagent:pending-choice` exit `0`。
- `pnpm run eval:wagent:planner-choice` exit `0`。
- `pending_choice_multi_candidate` 所有 required gates pass，尤其 `public_choice_payload_sanitized`。
- `planner_backed_choice` 所有 required gates pass，且 `planner_single_path_bypass_regression` 继续 pass。
- 新提交 artifacts / Markdown results 不包含 full `learned_path_id`、private map、slot overrides、
  selector、raw planner payload 或 raw response text 泄漏。
- 本包 review 明确记录未运行项；11.3.6 program 仍由后续 11.3.6.5 closeout 更新最终状态。
