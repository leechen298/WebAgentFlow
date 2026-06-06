# 11.3.10.2 Learning Outcome Gate Chat Feedback

状态：PACKAGE_COMPLETE
里程碑：M11.3 post-closeout
类型：code / mixed
父包：`11.3.10-autonomous-filter-capability-learning`
前置子包：`11.3.10.1-filter-capability-discovery-learning`

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [x] 混合型迭代

本包是 `11.3.10` 的第二个 executable child package。它只在 child 1 已经产生多场景
capability learning result 后实现。目标是让 `wagent chat` 根据真实学习结果反馈成功、
部分成功、失败或未验证，而不是根据单个 LearnedPath alias 输出“我学会了开始操作 / 帮我开始”。

## 依赖关系

Child 2 不负责发现筛选能力，也不负责生成 scenario matrix。它必须消费 child 1 提供的：

- capability summaries
- learned path ids
- failed scenario summaries
- unsupported capability summaries
- evidence warnings
- discovery batch id

child 1 未达到 `PACKAGE_COMPLETE` 前，本包不得进入 runtime implementation。当前
child 1 已完成非 live closeout，因此本包已完成 scoped implementation。

## 文档集

- `README.md` - 包索引、状态、前置依赖。
- `intent.md` - 用户反馈问题、产品目标、用户体验目标。
- `contract.md` - learning outcome 状态和 feedback contract。
- `technical-design.md` - aggregate result、chat runtime、history/debug timeline、CLI 设计。
- `test-plan.md` - outcome gate、控制词过滤、history、CLI 回归测试。
- `plan.md` - 实现顺序和 stop conditions。
- `review.md` - 设计复核、implementation authorization 和验证记录。

## 成功状态

学习完成后，用户看到的是“我实际学到了哪些能力 / 哪些没有学会 / 下一步怎么自然表达工作需求”，
而不是固定口令或控制词。

示例方向：

- 成功：`我学会了按状态搜索、按邮箱搜索、组合筛选用户。你可以直接告诉我想做什么，比如“搜索启用用户”或“按邮箱查用户”。`
- 部分成功：列出已学能力和失败/暂不支持能力。
- 失败或未验证：明确说学习失败或尚不能确认，并提供后台详情入口。

## Closeout Summary

本包已完成非 live runtime implementation。`wagent chat` 现在基于 aggregate
learning outcome 反馈结果：

- `failed` / `unverified` 不会被说成成功，也不会进入 session learned action catalog。
- success / partial_success 会列出学到的 capability，而不是输出“帮我开始”。
- 控制词不会进入 alias / suggested utterance / business goal / match terms。
- conversation history 记录 learning outcome、capability summaries、run ids 和
  LearnedPath ids。
- `wagent chat` 会记录 Ctrl+C / EOF / exit command 退出事件，并在会话开头提示
  `/conversation/history/<session_id>`。

Live autonomous validation 默认未运行，等待用户明确授权。

## 非目标

- 不实现 filter capability discovery；该工作属于 child 1。
- 不绕过 evidence gate 宣称成功。
- 不把失败或未验证 run 加入当前 session learned action catalog。
- 不强迫用户背诵固定口令。
- 不在文档阶段执行 live autonomous run。
