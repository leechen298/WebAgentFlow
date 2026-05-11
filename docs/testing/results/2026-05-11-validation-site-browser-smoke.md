# Validation-site Browser Smoke

Date: 2026-05-11
Commit: `818c30a564e2c2d61039f5ceb13f780c8a18e3dc`
Working tree: clean before this report was added (`git status --short` had no output)
Tool: Browser Use / in-app browser
Scope: validation-site `/login` and `/users` visual browser smoke

## Preconditions

- API health: PASS
  - Command: `curl -sS -i http://127.0.0.1:8001/health`
  - Result: HTTP 200, `{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}`
- validation-site `/login`: PASS
  - Command: `curl -sS -I http://127.0.0.1:5175/login`
  - Result: HTTP 200, `Content-Type: text/html`
- validation-site `/users`: PASS
  - Command: `curl -sS -I http://127.0.0.1:5175/users`
  - Result: HTTP 200, `Content-Type: text/html`

Notes:

- Initial default-sandbox localhost checks could not reach the services, and
  sandboxed dev-server startup failed with local bind permission errors.
- Non-sandbox service checks then confirmed the API and validation-site were
  already reachable on `127.0.0.1:8001` and `127.0.0.1:5175`.
- No product code, E2E spec, package script, or iteration document was changed.

## Summary

| Case | Status | Evidence |
| --- | --- | --- |
| VSB-001 · Login page renders key controls | PASS | Browser Use DOM observation plus visible screenshot displayed in the in-app browser output |
| VSB-002 · Login invalid credentials shows error | PASS | Browser Use fill/click observation; visible `role=alert` text `用户名或密码错误` |
| VSB-003 · Users page renders search controls | PASS | Browser Use DOM observation plus visible screenshot displayed in the in-app browser output |
| VSB-004 · Users search by name changes result area | PASS | Browser Use fill/click observation; URL changed to `?name=alice`, result count became `1 位用户` |
| VSB-005 · Users no-match search shows empty state | PASS | Browser Use fill/click observation plus visible no-match screenshot displayed in the in-app browser output |

## Case Results

### VSB-001 · Login page renders key controls

- Status: PASS
- Method: Browser Use / in-app browser
- Page URL: `http://127.0.0.1:5175/login`
- Visible actions:
  - Opened `/login`.
  - Observed the login page in the in-app browser.
- Visible observations:
  - Page title: `Sign in — Validation Site`.
  - Visible heading: `登录`.
  - Username textbox was visible.
  - Password textbox was visible.
  - Submit button `登录` was visible.
  - The error region is not rendered before an error because the Vue template
    uses `v-if="errorMessage"`; VSB-002 confirms the same `role=alert` region
    becomes visible after invalid credentials.
- Evidence:
  - Browser observation excerpt:

    ```json
    {
      "url": "http://127.0.0.1:5175/login",
      "title": "Sign in — Validation Site",
      "usernameCount": 1,
      "usernameVisible": true,
      "passwordCount": 1,
      "passwordVisible": true,
      "submitCount": 1,
      "submitVisible": true,
      "alertBeforeCount": 0
    }
    ```

  - A login-page screenshot with the error state was displayed in the Browser
    Use output; no screenshot file was committed.
- Notes: The default-hidden alert behavior is expected for this fixture.
- Follow-up: none.

### VSB-002 · Login invalid credentials shows error

- Status: PASS
- Method: Browser Use / in-app browser
- Page URL: `http://127.0.0.1:5175/login`
- Visible actions:
  - Filled username `wrong`.
  - Filled password `wrong`.
  - Clicked the login submit button.
- Visible observations:
  - Page stayed on `/login`.
  - A user-visible red alert appeared above the form.
  - Alert text: `用户名或密码错误`.
- Evidence:

  ```json
  {
    "url": "http://127.0.0.1:5175/login",
    "alertCount": 1,
    "alertVisible": true,
    "alertText": "用户名或密码错误"
  }
  ```

- Notes: This did not require verify-scenario or autonomous exploration.
- Follow-up: none.

### VSB-003 · Users page renders search controls

- Status: PASS
- Method: Browser Use / in-app browser
- Page URL: `http://127.0.0.1:5175/users`
- Visible actions:
  - Opened `/users`.
  - Waited for seeded users to render.
- Visible observations:
  - Page title: `User Directory — Validation Site`.
  - Visible heading: `用户目录`.
  - Search card `筛选条件` was visible.
  - Name search input was visible.
  - Status radio group was visible.
  - Search button `搜索` was visible.
  - Result table was visible.
  - Initial result count was `15 位用户`.
  - Seeded row `alice@example.com` was visible.
- Evidence:

  ```json
  {
    "url": "http://127.0.0.1:5175/users",
    "title": "User Directory — Validation Site",
    "nameCount": 1,
    "nameVisible": true,
    "statusCount": 1,
    "statusVisible": true,
    "searchCount": 1,
    "searchVisible": true,
    "tableCount": 1,
    "tableVisible": true,
    "aliceVisible": true,
    "countLabel": "15 位用户"
  }
  ```

  - A `/users` screenshot was displayed in the Browser Use output; no
    screenshot file was committed.
- Notes: The page loaded through the validation-site Vite server and proxied
  `/validation-api/*` calls to the local API.
- Follow-up: none.

### VSB-004 · Users search by name changes result area

- Status: PASS
- Method: Browser Use / in-app browser
- Page URL: `http://127.0.0.1:5175/users`
- Visible actions:
  - Filled the name input with `alice`.
  - Clicked `搜索`.
- Visible observations:
  - URL changed to `http://127.0.0.1:5175/users?name=alice`.
  - Result count changed to `1 位用户`.
  - Result row showed `alice`, `alice@example.com`, role `admin`, status `启用`.
- Evidence:

  ```json
  {
    "url": "http://127.0.0.1:5175/users?name=alice",
    "countLabel": "1 位用户",
    "aliceEmailVisible": true,
    "rowText": "1\talice\talice@example.com\tadmin\t启用\t2024-03-15\tEngineering\t查看"
  }
  ```

- Notes: This confirmed the visible result area changed after the search.
- Follow-up: none.

### VSB-005 · Users no-match search shows empty state

- Status: PASS
- Method: Browser Use / in-app browser
- Page URL: `http://127.0.0.1:5175/users`
- Visible actions:
  - Filled the name input with `zzzz-no-match-9999`.
  - Clicked `搜索`.
- Visible observations:
  - URL changed to
    `http://127.0.0.1:5175/users?name=zzzz-no-match-9999`.
  - Result count changed to `0 位用户`.
  - Empty state text `未找到匹配的用户` was visible in the result table.
- Evidence:

  ```json
  {
    "url": "http://127.0.0.1:5175/users?name=zzzz-no-match-9999",
    "countLabel": "0 位用户",
    "emptyVisible": true,
    "emptyText": "未找到匹配的用户"
  }
  ```

  - A no-match screenshot was displayed in the Browser Use output; no
    screenshot file was committed.
- Notes: The first attempted wait used the old English source expectation
  translated as `未找到用户`; a fresh browser snapshot showed the actual visible
  localized text is `未找到匹配的用户`, and the case was rerun with that visible
  UI text.
- Follow-up: none.

## Boundaries

- Autonomous endpoints called: no.
- `/exploration/autonomous-runs` called: no.
- `/exploration/autonomous-runs/stream` called: no.
- Autonomous explorer imported or run directly: no.
- verify-scenario used: no.
- LLM provider used: no.
- Product code modified: no.
- E2E spec modified: no.
- Package scripts modified: no.
- `docs/iterations/` modified: no.

## Raw Evidence Appendix

### Repository state

```text
$ git rev-parse HEAD
818c30a564e2c2d61039f5ceb13f780c8a18e3dc

$ git status --short
<no output>
```

### Service checks

```text
$ curl -sS -i http://127.0.0.1:8001/health
HTTP/1.1 200 OK
content-type: application/json

{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}

$ curl -sS -I http://127.0.0.1:5175/login
HTTP/1.1 200 OK
Content-Type: text/html

$ curl -sS -I http://127.0.0.1:5175/users
HTTP/1.1 200 OK
Content-Type: text/html
```

### Browser observation excerpts

Login page initial snapshot excerpt:

```text
- heading "登录" [level=1]
- generic: WebAgentFlow 验证站点
- generic: 用户名
- textbox "用户名"
- generic: 密码
- textbox "密码"
- button "登录"
- link "忘记密码？"
- link "联系管理员"
```

Users page initial snapshot excerpt:

```text
- banner:
  - heading "用户目录" [level=2]
- generic: 筛选条件
- textbox "例如 alice"
- generic "状态"
- radio "全部" [checked]
- button "搜 索"
- generic: 结果
- table:
```

Users no-match snapshot excerpt:

```text
- textbox "例如 alice": zzzz-no-match-9999
- generic: 结果
- generic: 0 位用户
- row "未找到匹配的用户"
```
