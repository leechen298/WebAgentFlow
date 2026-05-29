# 技术设计（Technical Design）

状态：NEEDS_USER_INPUT

## Current State

`external-black-box-validation-latest.md` currently records overall `FAIL`.
`11.3.8.1` through `11.3.8.4` completed repo-local repair and regression work, but
no live external revalidation has been run in this package.

## Design

This package is a validation workflow, not runtime implementation.

Flow:

```text
approval fields present?
  no -> NEEDS_USER_INPUT, stop
  yes -> pre-live checks
       -> approved product surface run
       -> integrity / redaction checks
       -> dated report
       -> latest report only if approved
       -> parent closeout status
```

## Pre-live Checks

After approval, run only allowed checks:

- `git status --short --branch`
- API health for the approved API base URL
- target health for the approved target URL
- forbidden target scan using child-owned manifest or temp manifest

## Live Validation Surface

Preferred:

```bash
.venv/bin/wagent chat --api-base <approved-api-base-url> --timeout 300 --headless
```

Do not call autonomous-run endpoints directly.

## Report Update Rules

- Create a dated report only from actual run evidence.
- Update latest report only when explicitly approved.
- If validation is not run, do not change latest report.
- If `PV-CLI-003` still fails, latest remains `FAIL` or equivalent honest status.

## Non-goals

- No code changes.
- No tests or runtime fixes.
- No browser smoke unless explicitly requested.
- No hidden validation surfaces.

## Exit Criteria

- If approval missing: `review.md` records `NEEDS_USER_INPUT` and lists missing fields.
- If approval present and validation runs: report records commands, scenario results,
  integrity checks, redaction checks, final status, and caveats.
- Parent 11.3.8 status is not set to `PASS` unless evidence supports all required gates.
