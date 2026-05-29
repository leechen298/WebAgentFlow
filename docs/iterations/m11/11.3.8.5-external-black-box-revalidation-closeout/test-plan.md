# 测试计划（Test Plan）

状态：NEEDS_USER_INPUT

## Boundary

No live validation may run until approval fields are recorded in `review.md`.

## Documentation Checks

```bash
find docs/iterations/m11/11.3.8.5-external-black-box-revalidation-closeout -maxdepth 1 -type f | sort
rg -n "External Black-box Revalidation|operator surface|PASS|FAIL|FOLLOW_UP|UNVERIFIED|Forbidden Changes|NEEDS_USER_INPUT" docs/iterations/m11/11.3.8.5-external-black-box-revalidation-closeout
git diff --check
```

## Pre-live Checks After Approval

Use approved values only:

```bash
git status --short --branch
curl -i <approved-api-base-url>/health
curl -i <approved-target-url>
```

Run forbidden target scan with a child-owned or temp manifest.

## Live Validation After Approval

Use approved product surface:

```bash
.venv/bin/wagent chat --api-base <approved-api-base-url> --timeout 300 --headless
```

Required scenarios by default:

- `PV-CLI-002`
- `PV-CLI-003`
- `PV-CLI-004`
- `PV-INTEGRITY-001`
- `PV-INTEGRITY-002`

Required reviewable artifacts:

- operator action log and `operator_actions` artifact;
- raw product-client request / response records for project CLI traffic;
- redacted JSON / Markdown artifacts;
- stable latest redacted record at a stable repo path, only if latest-result-doc
  update is approved;
- scenario result table with final status vocabulary.

## Not Run Until Approval

| Item | Status |
|---|---|
| live external black-box validation | not run |
| live `wagent chat` | not run |
| `verify-scenario` | not run |
| browser / UI smoke | not run |
| direct autonomous-run endpoint | forbidden |
| direct replay API product validation | forbidden |
| latest result docs update | not modified |

## Result Rules

- `PASS` only when required scenarios and integrity checks pass with reviewable evidence.
- `FAIL` when a required scenario contradicts expected behavior.
- `BLOCKED` when required services or allowed surfaces are unavailable.
- `UNVERIFIED` when evidence is incomplete.
- `FOLLOW_UP_REQUIRED` when evidence shows partial repair but incomplete product capability.
