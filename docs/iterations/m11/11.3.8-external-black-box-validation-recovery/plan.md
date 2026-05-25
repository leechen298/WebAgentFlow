# 实施计划（Plan）

状态：proposed

## 总体说明

本文件是 `11.3.8 External Black-box Validation Recovery` 的 umbrella plan。它只定义总包拆分、边界和实施顺序，不直接授权 runtime 代码修改。

每个子迭代进入实现前，必须创建自己的完整七件套：

```text
README.md
intent.md
contract.md
technical-design.md
test-plan.md
plan.md
review.md
```

后续实现 Agent 必须先读对应子迭代的 `contract.md`、已审核 `technical-design.md`、`test-plan.md` 和 `plan.md`，不得只凭本总包直接改 matcher 或 runtime。

## 11.3.8.1 Learning Action Goal Preservation

### Goal

让学习完成后的 session learned action metadata 保留 intake 中的业务目标。

当前失败中 intake 已有：

```text
action.goal = Create inventory item
canonical_goal = create_inventory_item
aliases = add inventory item / new inventory item / create new item
slots = sku, name, category, quantity
```

但最终 learned action metadata 只保留：

```text
alias = Learn how to create
utterances = 帮我Learn how to create / Learn how to create 一下
```

本子迭代修复这个断点。

### Why

如果 learning output 不保存业务动作，后续执行阶段没有可靠 match terms。单纯放宽 matcher 只能让当前 case 看起来能跑，却可能让系统更会乱猜。

### Expected output

- Product-level learning action label 优先来自 intake business goal。
- session learned action metadata 尽量保留：
  - `alias: Create inventory item`
  - `canonical_goal: create_inventory_item`
  - `business_object: inventory item`
  - meaningful aliases / match terms
- `Learn how to ...` 被视为教学 wrapper，而不是业务动作本体。
- slot values 保留为执行参数或 evidence，不进入 reusable action identity。

### Suspected files

后续子迭代可以优先检查：

```text
apps/api/app/services/learning/learning_run_service.py
apps/api/app/services/conversation/chat_runtime.py
apps/api/app/services/conversation/intake.py
apps/api/tests/test_learning_run_service.py
apps/api/tests/test_conversation_chat_runtime.py
```

### Non-goals

- 不硬编码 `inventory item`。
- 不硬编码 `5177/inventory`。
- 不依赖 Validation-Site 页面结构。
- 不修改外部 Validation-Site。
- 不把外部站点 selector、`data-testid`、component 或 seed copy 写入主仓库。

### Test focus

- English：`Learn how to create an inventory item...`。
- Chinese：`学习创建记录...` 或现有中文 product-level 学习场景。
- Existing product-level Chinese cases 不能回归。
- label 不能截断掉 business object。
- slot values 不能成为 action identity。

## 11.3.8.2 Suggested Utterance Generation

### Goal

生成可复用的 suggested utterances，不能只生成教学句式变体。

当前坏结果：

```text
帮我Learn how to create
Learn how to create 一下
```

期望方向：

```text
Create inventory item
Help me create inventory item
帮我创建库存项
```

中文不要求一步到位做到完整翻译系统，但英文业务对象不能丢。

### Why

suggested utterances 同时影响用户提示和后续 match terms。如果 utterances 只来自泛化教学 wrapper，用户用自然业务表达执行时仍然无法命中。

### Expected output

- utterances 基于 canonical business goal 和 original action goal。
- aliases 中有价值的业务表达被保留。
- 避免从 `Learn how to create` 直接套 `帮我{label}`。
- 可以同时包含 normalized English action、original action goal 和现有行为需要的轻量中文 wrapper。

### Suspected files

```text
apps/api/app/services/learning/learning_run_service.py
apps/api/app/services/conversation/chat_runtime.py
apps/api/tests/test_learning_run_service.py
apps/api/tests/test_conversation_chat_runtime.py
```

### Non-goals

- 不做完整多语言翻译系统。
- 不引入 LLM 生成 utterance 的新依赖。
- 不把外部站点字段、SKU、库存 seed 或 selector 写死成 utterance。
- 不让 suggested utterances 泄漏敏感值或 private payload。

### Test focus

- learning result includes utterance matching execute intent。
- old Chinese learned action tests still pass。
- sensitive values must not leak into suggested utterances。
- slot values should not become part of reusable action identity。

## 11.3.8.3 Learned Action Matching Improvement

### Goal

让执行阶段可以基于 business goal、canonical goal、aliases、business object 等 match terms 匹配已学 action，而不是只靠 literal alias / utterances。

当前失败：

```text
learned action terms:
  learnhowtocreate
  learnhowtocreate一下

execute terms:
  Create inventory item
  create_inventory_item

match = 0
```

### Why

PV-CLI-003 中 router 已能看出页面有 learned action context，但 runtime 需要具体 `_match_session_action()` 结果才能进入 replay。matcher 的语义输入太窄，导致它无法绑定已学 action。

### Expected output

- session learned action metadata 存储更丰富的 match terms。
- matcher 比较：
  - alias
  - utterances
  - canonical goal
  - normalized business goal
  - business object
  - meaningful aliases
- matching 不能只看 raw substring。
- 同一业务动作的新 slot values 可以命中已学 action。
- 多候选或低置信度匹配进入 choice / clarification。

### Suspected files

```text
apps/api/app/services/conversation/chat_runtime.py
apps/api/app/services/conversation/router_agent.py
apps/api/tests/test_conversation_chat_runtime.py
apps/api/tests/test_conversation_router_agent.py
```

### Safety constraints

- 如果多个 learned actions 都可能匹配，应走 pending choice / planner choice，不应自动猜。
- 如果只有低置信度匹配，应 ask user，而不是执行。
- 不应因为共享动词 `create` / `open` / `update` 就匹配。
- business object 或 canonical goal 必须参与判断。
- eval-only candidate binding 不能被宣称为 full live product capability。

### Non-goals

- 不绕过 session learned action binding。
- 不调用 direct replay API 作为 WAgent chat pass evidence。
- 不把 direct service import 的结果当作产品验证。
- 不用外部站点 answer key 调整 matcher。

### Test focus

- learn `Create inventory item` -> execute `Create inventory item with new values` => match。
- learn `Create inventory item` -> execute `Search inventory item` => no direct match。
- learn `Create inventory item` + `Search inventory item` -> execute ambiguous inventory request => choice required。
- learn generic `Create` -> execute `Create inventory item` => should not overmatch unless business object exists。

## 11.3.8.4 Regression Tests

### Goal

把 PV-CLI-003 的失败模式固化成 automated regression。

### Why

外部黑盒验证不应成为唯一防线。核心 semantic chain 应该在不依赖外部站点的情况下通过 unit / service / integration-ish tests 覆盖。

### Expected output

Unit / service tests 覆盖：

```text
learning_run_service label preservation
suggested utterance generation
match term normalization
chat_runtime action matching
router known learned action counting
```

Integration-ish API 或 service-level tests 覆盖：

```text
simulate learn input:
  Learn how to create an inventory item ...

then execute input:
  Create an inventory item with new values ...

assert:
  learned action metadata contains create inventory item
  execute matches learned action
  replay handler called with new slot overrides
```

### Suspected files

```text
apps/api/tests/test_learning_run_service.py
apps/api/tests/test_conversation_chat_runtime.py
apps/api/tests/test_conversation_router_agent.py
```

如果现有测试已有更合适的 helper 或 fake replay handler，应优先复用，避免新增重复 fixtures。

### Non-goals

- 不把 `5177/inventory` 写入 automated tests as hard dependency。
- 不依赖 WebAgentFlow-Validation-Site 运行。
- 不使用外部站点 selector。
- 不复制外部站点 `data-testid`、component、seed copy。
- 不恢复 archived eval。
- 不把旧 `5176/items` runtime eval 改回 active 默认 eval。

### Test focus

- English learn-create-inventory -> execute-new-values。
- business object preserved。
- suggested utterance contains business object。
- wrong action does not execute。
- ambiguous learned actions require choice。
- old generic / Chinese behavior remains compatible where covered。

## 11.3.8.5 External Black-box Revalidation / Closeout

### Goal

修复后重跑外部黑盒验证，证明 product-like path 改善，并更新 result docs。

### Why

Automated regression 证明代码路径，external black-box revalidation 证明用户视角产品路径。两者不能互相替代。

### Required rerun

至少重跑：

```text
PV-CLI-002
PV-CLI-003
PV-CLI-004
PV-INTEGRITY-001
PV-INTEGRITY-002
```

可选重跑：

```text
PV-SITE-001
PV-CLI-001
```

### Preconditions

- API running。
- `WebAgentFlow-Validation-Site` running at operator-provided `5177/inventory`。
- Prefer clean local DB；如果不是 clean DB，必须显式记录 DB state。
- No direct autonomous-run endpoint usage by operator。
- WAgent operator surface must be recorded。

### Expected output

更新：

```text
docs/testing/results/external-black-box-validation-latest.md
```

新增日期结果：

```text
docs/testing/results/external-black-box-validation-YYYYMMDD.md
```

如果仍然 `FAIL`，必须如实记录，不允许改成 `PASS`。如果 learning label 已修但 final execution evidence 仍不足，应记录 `FOLLOW_UP` / `UNVERIFIED`，不能扩大结论。

### Non-goals

- 不通过 direct `/exploration/autonomous-runs` 调用产生产品验证结果。
- 不通过 hidden HTTP client、service import、direct replay API 代替 `wagent chat` 或明确允许的产品表面。
- 不将 manual smoke alone 报告成完整 product capability pass。
- 不隐瞒 failed / blocked / unverified gates。

### Test focus

- `PV-CLI-002` learned action label is meaningful。
- `PV-CLI-003` starts execution for matching learned action。
- final response includes visible evidence or honest uncertainty。
- integrity scan remains pass。
- latest report records exact `PASS` / `FAIL` / `FOLLOW_UP` outcome。

## 实施顺序

1. 先生成 11.3.8.1 子迭代七件套并修 learning action goal preservation。
2. 再生成 11.3.8.2 子迭代七件套并修 suggested utterance generation。
3. 再生成 11.3.8.3 子迭代七件套并修 learned action matching。
4. 再生成 11.3.8.4 子迭代七件套并补 regression tests。
5. 最后生成 11.3.8.5 子迭代七件套并执行 external black-box revalidation / closeout。

如果实现中发现前置设计错误，应停止代码实现，先更新对应子迭代文档并完成 review，再继续。
