# Test Plan

## Test Boundary

This package tests outcome classification, chat feedback, control-term filtering,
learned action catalog gating, and history/debug timeline visibility.

Live autonomous browser execution is not part of the default test plan.

## Unit Tests

### Learning Outcome Derivation

Required coverage:

- passed capabilities only -> `success`
- passed + failed -> `partial_success`
- passed + unsupported -> `partial_success`
- no passed + failed -> `failed`
- no passed + unverified -> `unverified`
- systemic blocker with no passed capability -> `failed` or `unverified` according to evidence status

### Control Term Filtering

Required coverage:

- `开始学习` rejected as alias
- `取消` rejected as alias
- `是` / `好的` / `现在开始` rejected in suggested utterances
- control terms rejected from `business_goal`
- control terms rejected from `canonical_goal`
- control terms rejected from `match_terms`
- real business terms such as login / create record / search active users remain accepted

### Feedback Builder

Required coverage:

- success feedback lists learned capabilities
- success feedback does not contain “帮我开始”
- success feedback does not require fixed command phrases
- partial success feedback lists learned and failed/unverified capabilities
- failed feedback does not claim learning complete
- unverified feedback does not claim learning complete
- feedback uses “我” instead of exposing internal product name

## Service / API Tests

Required coverage:

- `chat_runtime.py` learning completion uses aggregate outcome
- failed/unverified result does not create session learned action
- partial success creates session learned actions only for passed capabilities
- success creates learned actions from passed LearnedPath capability metadata
- history detail includes outcome, capability summaries, run ids, learned path ids, and evidence status
- CLI session start includes `/conversation/history/<session_id>` path

## Regression Tests

Required regression:

- the URL-only learning flow cannot output “我学会了开始操作”
- the suggested next utterance cannot be “帮我开始”
- explicit business learning scenarios still produce natural identity when evidence passes
- previously learned actions remain executable through existing matching path

## Live Run Boundary

Default status: `not run`.

If a later user explicitly authorizes live validation, record:

- target URL
- session id
- learning batch outcome
- run ids
- learned path ids
- pass gate statuses
- raw product-client invocation surface

No direct autonomous-run endpoint calls are allowed.
