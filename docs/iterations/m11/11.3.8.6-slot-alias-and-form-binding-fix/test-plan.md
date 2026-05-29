# 测试计划（Test Plan）

状态：PACKAGE_COMPLETE

## Required RED/GREEN Tests

### Action Planner

Add a focused test in `apps/api/tests/test_action_planner.py` proving a
multi-field create-style form binds:

- `sku` -> exact `SKU` field, not search;
- `item_name` -> `Name`;
- `item_category` -> `Category`;
- `quantity` -> `Stock quantity`.

The test must include a search input whose placeholder mentions SKU/name/category
so the old prominence fallback would choose incorrectly.

### Chat Runtime

Add a focused test in `apps/api/tests/test_conversation_chat_runtime.py` proving:

- learned path supports `sku`, `item_name`, `item_category`, `quantity`;
- execute intake emits `sku`, `name`, `category`, `stock_quantity`;
- replay receives slot overrides keyed as learned slots:
  `sku`, `item_name`, `item_category`, `quantity`;
- no `unsupported_value_slot` event is emitted.

Add a negative test proving unrelated unsupported slots still block.

Add a focused test proving object-prefixed execute semantic types such as
`<object>_sku`, `<object>_name`, `<object>_category`, and `<object>_quantity`
map only by exact supported learned-slot suffix and replay receives learned
slot keys.

## Required Commands

```bash
cd apps/api && ../../.venv/bin/python -m pytest tests/test_action_planner.py -q
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q -k "slot_alias or unsupported"
cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py tests/test_action_planner.py -q
cd apps/api && ../../.venv/bin/python -m ruff check app/services/learning/action_planner.py app/services/conversation/chat_runtime.py tests/test_action_planner.py tests/test_conversation_chat_runtime.py
rg -n "5177|/inventory|inventory item|WebAgentFlow-Validation-Site" apps/api/app/services apps/api/app/prompts apps/cli/wagent apps/console/src packages
git diff --check
```

## Live Rerun

After focused tests pass and no P0 / P1 review findings remain, rerun approved
`11.3.8.5` scenarios through:

```bash
.venv/bin/wagent chat --api-base http://127.0.0.1:8001 --timeout 300 --headless
```

The rerun remains bound to the parent five-field approval gate. Current-thread
approval already provided: API base URL `http://127.0.0.1:8001`, target URL
`http://127.0.0.1:5177/inventory`, DB state policy `clean database`, approved
scenario list `all`, and latest-result-doc update approval `yes`.

Do not call autonomous-run endpoints directly.
