# Clean-Slate `/users` Live Validation Latest

Date: 2026-06-05

Final status: `FAIL`

Reason: `wagent chat` reached the requested product entry and triggered URL-only learning, and backend learning produced multiple filter scenario runs and LearnedPaths. However, the chat product surface timed out after the configured 300 seconds, never emitted a learning outcome, and the conversation session remained in `active_task.status=learning`. The required user-facing learning-complete feedback and post-learning natural task check were not reached.

`verify-scenario` was not run.

## Scope

- Product entry: `.venv/bin/wagent chat --api-base http://127.0.0.1:8001 --timeout 300`
- Live target: `http://127.0.0.1:5177/users`
- Reset scope: local dev PostgreSQL and Redis DB 0
- Forbidden surfaces avoided: no direct `POST /exploration/autonomous-runs`, no direct autonomous service import, no hidden Playwright run
- Evidence review: main thread operated reset/chat/read-only DB queries; subagents performed read-only evidence review

## Preflight

Target availability:

```text
curl -sI http://127.0.0.1:5177/users
HTTP/1.1 200 OK
```

API health:

```text
curl -i http://127.0.0.1:8001/health
{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}
```

Local containers:

```text
web-agent-flow-postgres  Up 23 hours (healthy)  0.0.0.0:5432->5432/tcp
web-agent-flow-redis     Up 23 hours (healthy)  0.0.0.0:6379->6379/tcp
web-agent-flow-minio     Up 23 hours (healthy)  0.0.0.0:9000-9001->9000-9001/tcp
```

Git scope note: worktree was already dirty with existing 11.3.10 / 11.3.11 and other untracked changes. This validation did not revert, clean, or stage those changes.

## Clean Slate Reset

PostgreSQL reset command:

```sql
TRUNCATE TABLE
  conversation_messages,
  conversation_events,
  conversation_sessions,
  learned_paths,
  exploration_runs
RESTART IDENTITY CASCADE;
```

Redis reset command:

```text
FLUSHDB
```

Post-reset counts:

```text
conversation_events    0
conversation_messages  0
conversation_sessions  0
exploration_runs       0
learned_paths          0
```

## Chat Transcript

Command:

```bash
.venv/bin/wagent chat --api-base http://127.0.0.1:8001 --timeout 300
```

Session:

```text
session_id: 697a6957-f458-4c02-bfb8-2ae617470aef
history: /conversation/history/697a6957-f458-4c02-bfb8-2ae617470aef
```

Transcript:

```text
WAgent > 本次会话 ID：697a6957-f458-4c02-bfb8-2ae617470aef。调试详情：/conversation/history/697a6957-f458-4c02-bfb8-2ae617470aef
WAgent > 你好，我可以学习页面操作，也可以执行已经学会的操作。
You > http://127.0.0.1:5177/users
WAgent > 我已收到这个页面地址。我可以开始学习这个页面上的操作，学会后再帮你执行。
WAgent > 要现在开始吗？
WAgent ? 要现在开始吗？ 开始学习
WAgent > 开始学习页面操作。
wagent chat: HTTP error - timed out
```

Exit: code `2` after about 300 seconds.

Per the validation plan, no retry was performed after the timeout.

## Conversation State

Conversation messages after timeout:

```text
user   http://127.0.0.1:5177/users
agent  我已收到这个页面地址。我可以开始学习这个页面上的操作，学会后再帮你执行。\n要现在开始吗？
user   开始学习
agent  开始学习页面操作。
```

Compact event evidence:

```text
chat_learning_started  url=http://127.0.0.1:5177/users
```

No compact event showed `learning_outcome`, learning completion, failed learning feedback, or learned capability summary.

Final session row:

```text
status=task_intake
current_mode=interactive_chat
active_task.status=learning
active_task.goal=学习这个页面上的操作
pending_target.url=http://127.0.0.1:5177/users
updated_at=2026-06-05 09:13:26.543711+00
```

## DB Snapshot

The DB was not quiescent after the CLI timeout. Backend learning continued to write new runs and LearnedPaths while the chat session stayed stuck in `learning`.

Observed counts immediately before writing the first evidence table:

```text
conversation_events    21
conversation_messages  4
conversation_sessions  1
exploration_runs       21
learned_paths          16
```

Observed counts about 15 seconds later:

```text
conversation_events    21
conversation_messages  4
conversation_sessions  1
exploration_runs       24
learned_paths          18
```

Scenario distribution read during the later observation:

```text
single_filter    8
pairwise_filter  17
```

Important note: a count query and a distribution query were not consistent because backend writes were still occurring. Therefore the run and LearnedPath tables below are captured evidence snapshots, not a closed learning batch. This is itself part of the failure evidence.

## Exploration Runs Snapshot

Each listed run had `terminal_outcome=terminal_detected`, `stop_decision=stop`, and `matched_action_ids=1`.

```text
run_id                                kind             label                              pass_gate  terminal_type  ingest
7dddda30-36bb-4cfa-bbce-b3bd89e78a64  single_filter    Search by 姓名                     pass       navigation     eligible
d91bf1cc-e5c9-4436-9976-38ab8a2e6bab  single_filter    Search by 邮箱                     pass       navigation     eligible
007ec688-a5c9-43be-8bec-62b24c6ba992  single_filter    Search by 注册开始                 pass       list_refresh   eligible
dfd03d9e-bc3b-4abb-9c3c-bf81d84030c5  single_filter    Search by 注册结束                 pass       list_refresh   eligible
9203ca0f-7fb9-45a8-8911-6fbe4eb37673  single_filter    Search by 地区                     pass       list_refresh   eligible
aa243789-0a71-4380-bc18-82cbd94866f9  single_filter    Search by 月份                     pass       list_refresh   eligible
10cff9a2-d1e2-4620-9ebf-0d3fc161b305  single_filter    Search by 状态: active             [empty]    list_refresh   [empty]
ce1cbf65-b88c-487a-8a9e-4834cf9ab68a  single_filter    Search by 状态: disabled           [empty]    list_refresh   [empty]
f0648381-7666-43ba-a89a-fd3bd5bbb233  pairwise_filter  Search by 姓名 + 邮箱              pass       navigation     eligible
956e4633-d5af-478e-92de-98db1f63734e  pairwise_filter  Search by 姓名 + 注册开始          pass       navigation     eligible
80404c5b-2075-4f26-b73d-d194eba27c1e  pairwise_filter  Search by 姓名 + 注册结束          pass       navigation     eligible
f7543899-2e5d-4436-9d6a-c92991fec2c0  pairwise_filter  Search by 姓名 + 地区              pass       navigation     eligible
90f5c633-712a-402e-836f-3ddb1fbf033e  pairwise_filter  Search by 姓名 + 月份              pass       navigation     eligible
6aec3fff-151f-45fc-9be2-75fc7fdfd89a  pairwise_filter  Search by 姓名 + 状态: active      [empty]    navigation     [empty]
43030e6f-e118-4eb5-9450-25095ea5454e  pairwise_filter  Search by 姓名 + 状态: disabled    [empty]    navigation     [empty]
808558c6-d59e-4068-bc7e-b213bffcc039  pairwise_filter  Search by 邮箱 + 注册开始          pass       navigation     eligible
5e059374-cba6-409a-ac8a-b74078a2d976  pairwise_filter  Search by 邮箱 + 注册结束          pass       navigation     eligible
6886fd8c-13a5-4484-b6c2-6fbbb2da878b  pairwise_filter  Search by 邮箱 + 地区              pass       navigation     eligible
96f2bafc-fbed-4a65-bc34-7ed52918ce02  pairwise_filter  Search by 邮箱 + 月份              pass       navigation     eligible
e36d6d45-b317-4ed2-af55-5bfaef8a2a01  pairwise_filter  Search by 邮箱 + 状态: active      [empty]    navigation     [empty]
f87ef383-88d9-4242-9a60-61fd9ad333f6  pairwise_filter  Search by 邮箱 + 状态: disabled    [empty]    navigation     [empty]
26b7275c-5d35-4164-afae-ffd00f4954f5  pairwise_filter  Search by 注册开始 + 注册结束      pass       list_refresh   eligible
```

Run evidence interpretation:

- The old issue "only clicked a search/start button" did not reproduce in backend run data.
- There are multiple `single_filter` and `pairwise_filter` scenarios.
- Runs with empty pass/ingest fields did not produce LearnedPaths in the inspected evidence.
- Terminal evidence is action-scoped for sampled ingested runs.

This snapshot is partial because backend writes continued after the chat timeout.

## LearnedPaths Snapshot

```text
learned_path_id                         source_run_id                          kind             label                              pass_gate  terminal             ingest
81ca076f-acfe-4906-afc7-8263b009032c    7dddda30-36bb-4cfa-bbce-b3bd89e78a64   single_filter    Search by 姓名                     pass       terminal_detected    eligible
787d10c6-5a27-461b-94e5-009d4505461a    d91bf1cc-e5c9-4436-9976-38ab8a2e6bab   single_filter    Search by 邮箱                     pass       terminal_detected    eligible
234a3d9a-962a-4c19-9c4f-71aa071877ea    007ec688-a5c9-43be-8bec-62b24c6ba992   single_filter    Search by 注册开始                 pass       terminal_detected    eligible
9879ce70-f076-4839-b2f8-16f32288a446    dfd03d9e-bc3b-4abb-9c3c-bf81d84030c5   single_filter    Search by 注册结束                 pass       terminal_detected    eligible
e30a838f-e4dc-46d2-a3fd-ed6c030344bc    9203ca0f-7fb9-45a8-8911-6fbe4eb37673   single_filter    Search by 地区                     pass       terminal_detected    eligible
69d06cc0-46b6-40d3-b49e-688a31313e61    aa243789-0a71-4380-bc18-82cbd94866f9   single_filter    Search by 月份                     pass       terminal_detected    eligible
a7324ad7-6f49-48ce-ae39-df3cc64bb970    f0648381-7666-43ba-a89a-fd3bd5bbb233   pairwise_filter  Search by 姓名 + 邮箱              pass       terminal_detected    eligible
ce2f2661-a4a3-41cf-9fd0-bc00ccc96190    956e4633-d5af-478e-92de-98db1f63734e   pairwise_filter  Search by 姓名 + 注册开始          pass       terminal_detected    eligible
f411070f-cee7-4b49-8731-db45c2a195f6    80404c5b-2075-4f26-b73d-d194eba27c1e   pairwise_filter  Search by 姓名 + 注册结束          pass       terminal_detected    eligible
2dfcff77-3786-46fa-8de8-fd13a95144b5    f7543899-2e5d-4436-9d6a-c92991fec2c0   pairwise_filter  Search by 姓名 + 地区              pass       terminal_detected    eligible
4b5806c2-01e0-4455-aa2a-deac30bc2da2    90f5c633-712a-402e-836f-3ddb1fbf033e   pairwise_filter  Search by 姓名 + 月份              pass       terminal_detected    eligible
9dc15c80-6934-4c5d-b643-f22ff16428c3    808558c6-d59e-4068-bc7e-b213bffcc039   pairwise_filter  Search by 邮箱 + 注册开始          pass       terminal_detected    eligible
4018e1a1-3eb6-4e2c-a576-81d6ca24b32b    5e059374-cba6-409a-ac8a-b74078a2d976   pairwise_filter  Search by 邮箱 + 注册结束          pass       terminal_detected    eligible
eb71ee44-047c-490c-afb6-9d0d3b6a21b6    6886fd8c-13a5-4484-b6c2-6fbbb2da878b   pairwise_filter  Search by 邮箱 + 地区              pass       terminal_detected    eligible
d7f742bf-2b79-4e63-b284-1ff21b8304db    96f2bafc-fbed-4a65-bc34-7ed52918ce02   pairwise_filter  Search by 邮箱 + 月份              pass       terminal_detected    eligible
5fc53fd9-d5aa-4285-ac74-f84072b62207    26b7275c-5d35-4164-afae-ffd00f4954f5   pairwise_filter  Search by 注册开始 + 注册结束      pass       terminal_detected    eligible
```

Action summary from inspected LearnedPaths:

- Search by 姓名: `fill,click,observe`, selectors `#search-name,#btn-search`
- Search by 邮箱: `fill,click,observe`, selectors `#search-email,#btn-search`
- Several date/month-labeled scenarios used selectors containing `#search-region`, which is a semantic binding risk.

This snapshot is partial because backend writes continued after the chat timeout.

## Terminal / Ingest Evidence

Sampled ingested run: `7dddda30-36bb-4cfa-bbce-b3bd89e78a64`.

Key evidence:

```text
browser_event_timeline:
  request/response: /api/users
  framenavigated: /users?name=...
  action_id: action-step-1
  step_index: 1
  action_type: click

terminal_state_verdict:
  source=deterministic
  terminal_outcome=terminal_detected
  terminal_type=navigation
  stop_decision=stop
  matched_action_ids=[action-step-1]
  matched_step_indices=[1]
  matched_action_types=[click]

attempt_ingest_evaluation:
  pass_gate_status=pass
  ingest_status=eligible
  terminal_outcome=terminal_detected
  effective_action_count=2
```

Caveat: the sampled run still had an older top-level `success=false` / `verdict=failure` value caused by a stale CAPTCHA signal, while the Supervisor and attempt ingest evidence classified the search as successful. The terminal/ingest gate is internally coherent, but the cross-layer status inconsistency should remain visible.

## Subagent Review Findings

Subagent A: transcript / UX review

- No evidence of "帮我开始" or "我学会了开始操作".
- No evidence that "开始学习" became a learned action alias.
- No learning completion feedback appeared.
- UX dimension: `FAIL`.

Subagent B: run / path discovery review

- The old "only learned a single button/start operation" issue did not reproduce.
- Multi-scenario discovery evidence exists.
- Data dimension: `PASS_WITH_CAVEATS`.
- P1 caveat: some date/month labels appear bound to `#search-region`, so semantic correctness is not proven for every LearnedPath.
- P2 caveat: synthetic values such as `test_姓名` are repeatedly reused and often return empty result sets.

Subagent C: terminal / ingest review

- Ingested LearnedPaths satisfy action-scoped terminal evidence and eligible ingest gate in the inspected evidence.
- Runs without pass/eligible evidence were not ingested as LearnedPaths.
- Terminal/ingest dimension: `PASS`.
- Caveat: top-level old `success=false` / `verdict=failure` conflicts with attempt ingest pass for sampled run and should be cleaned up in a later implementation.

## Product Findings

P1: Chat learning outcome does not return to the user.

- Evidence: CLI timed out after 300 seconds; conversation session stayed `active_task.status=learning`; no learning outcome event or capability summary was emitted.
- Impact: the user cannot know what was learned, cannot move into a natural post-learning task in the same session, and the product surface fails this live validation even though backend learning continued.

P1: Backend learning continues after the chat client timeout without a closed batch handoff.

- Evidence: after the CLI timed out, counts kept growing from `exploration_runs=21 / learned_paths=16` to at least `exploration_runs=24 / learned_paths=18`, while conversation messages stayed at 4 and the session remained `active_task.status=learning`.
- Additional operator observation: after the CLI had exited, API logs continued to show autonomous exploration steps, Playwright continued to open `Google Chrome for Testing`, and a process check still showed a Playwright driver plus Chromium child processes while no `wagent chat` process was visible.
- Impact: clean batch accounting is not available through the chat surface, and a later conversation cannot safely infer a completed learning result from this session.

P1: Some capability labels do not match the apparent bound selector.

- Evidence: multiple date/month-labeled LearnedPaths used `#search-region` in action summaries.
- Impact: backend can prove multiple action-scoped terminal states, but cannot cleanly prove all LearnedPaths are semantically correct capabilities.

P2: Scenario input values are synthetic and low-hit.

- Evidence: repeated `test_姓名` style values, especially in pairwise scenarios.
- Impact: zero-result search is an acceptable terminal state when request completion / list refresh is observed, but it is weaker than using a real sample value from the page or response data.
- Non-specialized improvement direction: Page Understanding Agent should provide target-agnostic page purpose, visible table columns, current row values, filter-to-result hints, candidate terminal states, and sample value candidates. Scenario generation should prefer observed or response-derived values when available, while still allowing empty-result terminal states as valid but lower-confidence evidence.

## Acceptance Criteria Result

- Clean slate reset: `PASS`
- `wagent chat` created a new session and triggered learning: `PASS`
- Learning feedback success / partial_success with concrete capabilities: `FAIL`
- No "帮我开始" regression in transcript: `PASS`
- Not only a single button LearnedPath: `PASS`
- Multiple capability scenario runs: `PASS`
- At least one LearnedPath with action-scoped terminal evidence: `PASS`
- Failed / unverified scenarios excluded from LearnedPath: `PASS` in inspected evidence
- Same-session natural task check: `NOT RUN`, because the CLI timeout stop condition was hit
- Closed learning batch available through chat: `FAIL`

Overall: `FAIL`.
