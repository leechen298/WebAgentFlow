# Fixture-site 浏览器冒烟

日期：2026-05-11
Commit: `818c30a564e2c2d61039f5ceb13f780c8a18e3dc`
工作区：本报告添加前为 clean（`git status --short` 无输出）
工具：Browser Use / in-app browser
范围：fixture-site `/entry` 和 `/records` 可视化浏览器冒烟

## 前置条件

- API health: PASS
  - 命令：`curl -sS -i http://127.0.0.1:8001/health`
  - 结果：HTTP 200, `{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}`
- fixture-site `/entry`: PASS
  - 命令：`curl -sS -I https://example.invalid/entry`
  - 结果：HTTP 200, `Content-Type: text/html`
- fixture-site `/records`: PASS
  - 命令：`curl -sS -I https://example.invalid/records`
  - 结果：HTTP 200, `Content-Type: text/html`

备注：

- Initial default-sandbox localhost checks could not reach the services, and
  sandboxed dev-server startup failed with local bind permission errors.
- Non-sandbox service checks then confirmed the API and fixture-site were
  already reachable on `127.0.0.1:8001` and `127.0.0.1:5175`.
- No product code, E2E spec, package script, or iteration document was changed.

## 摘要

| 用例 | 状态 | 证据 |
| --- | --- | --- |
| VSB-001 · Login 页面渲染关键控件 | PASS | Browser Use DOM observation plus visible screenshot displayed in the in-app browser output |
| VSB-002 · Login 错误账号密码显示错误提示 | PASS | Browser Use fill/click observation; visible `role=alert` text `用户名或密码错误` |
| VSB-003 · Users 页面渲染搜索控件 | PASS | Browser Use DOM observation plus visible screenshot displayed in the in-app browser output |
| VSB-004 · Users 按 name 搜索会更新结果区域 | PASS | Browser Use fill/click observation; URL changed to `?name=alice`, result count became `1 位用户` |
| VSB-005 · Users 无匹配搜索显示 empty state | PASS | Browser Use fill/click observation plus visible no-match screenshot displayed in the in-app browser output |

## 用例结果

### VSB-001 · Login 页面渲染关键控件

- 状态：PASS
- 方法：Browser Use / in-app browser
- 页面 URL：`https://example.invalid/entry`
- 可见操作：
  - Opened `/entry`.
  - Observed the login page in the in-app browser.
- 可见观察：
  - Page title: `Sign in — Validation Site`.
  - Visible heading: `登录`.
  - Username textbox was visible.
  - Password textbox was visible.
  - Submit button `登录` was visible.
  - The error region is not rendered before an error because the Vue template
    uses `v-if="errorMessage"`; VSB-002 confirms the same `role=alert` region
    becomes visible after invalid credentials.
- 证据：
  - Browser observation excerpt:

    ```json
    {
      "url": "https://example.invalid/entry",
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
- 备注：默认隐藏 alert 是该 fixture 的预期行为。
- 后续：无。

### VSB-002 · Login 错误账号密码显示错误提示

- 状态：PASS
- 方法：Browser Use / in-app browser
- 页面 URL：`https://example.invalid/entry`
- 可见操作：
  - Filled username `wrong`.
  - Filled password `wrong`.
  - Clicked the login submit button.
- 可见观察：
  - Page stayed on `/entry`.
  - A user-visible red alert appeared above the form.
  - Alert text: `用户名或密码错误`.
- 证据：

  ```json
  {
    "url": "https://example.invalid/entry",
    "alertCount": 1,
    "alertVisible": true,
    "alertText": "用户名或密码错误"
  }
  ```

- 备注：不需要 verify-scenario 或 autonomous exploration。
- 后续：无。

### VSB-003 · Users 页面渲染搜索控件

- 状态：PASS
- 方法：Browser Use / in-app browser
- 页面 URL：`https://example.invalid/records`
- 可见操作：
  - Opened `/records`.
  - Waited for seeded users to render.
- 可见观察：
  - Page title: `User Directory — Validation Site`.
  - Visible heading: `用户目录`.
  - Search card `筛选条件` was visible.
  - Name search input was visible.
  - Status radio group was visible.
  - Search button `搜索` was visible.
  - Result table was visible.
  - Initial result count was `15 位用户`.
  - Seeded row `alice@example.com` was visible.
- 证据：

  ```json
  {
    "url": "https://example.invalid/records",
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

  - A `/records` screenshot was displayed in the Browser Use output; no
    screenshot file was committed.
- 备注：页面通过 fixture-site Vite server 加载，并代理
  `/validation-api/*` calls to the local API.
- 后续：无。

### VSB-004 · Users 按 name 搜索会更新结果区域

- 状态：PASS
- 方法：Browser Use / in-app browser
- 页面 URL：`https://example.invalid/records`
- 可见操作：
  - Filled the name input with `alice`.
  - Clicked `搜索`.
- 可见观察：
  - URL changed to `https://example.invalid/records?name=alice`.
  - Result count changed to `1 位用户`.
  - Result row showed `alice`, `alice@example.com`, role `admin`, status `启用`.
- 证据：

  ```json
  {
    "url": "https://example.invalid/records?name=alice",
    "countLabel": "1 位用户",
    "aliceEmailVisible": true,
    "rowText": "1\talice\talice@example.com\tadmin\t启用\t2024-03-15\tEngineering\t查看"
  }
  ```

- 备注：确认搜索后可见结果区域发生变化。
- 后续：无。

### VSB-005 · Users 无匹配搜索显示 empty state

- 状态：PASS
- 方法：Browser Use / in-app browser
- 页面 URL：`https://example.invalid/records`
- 可见操作：
  - Filled the name input with `zzzz-no-match-9999`.
  - Clicked `搜索`.
- 可见观察：
  - URL changed to
    `https://example.invalid/records?name=zzzz-no-match-9999`.
  - Result count changed to `0 位用户`.
  - Empty state text `未找到匹配的用户` was visible in the result table.
- 证据：

  ```json
  {
    "url": "https://example.invalid/records?name=zzzz-no-match-9999",
    "countLabel": "0 位用户",
    "emptyVisible": true,
    "emptyText": "未找到匹配的用户"
  }
  ```

  - A no-match screenshot was displayed in the Browser Use output; no
    screenshot file was committed.
- 备注：第一次等待使用了旧英文源码预期，
  translated as `未找到用户`; a fresh browser snapshot showed the actual visible
  localized text is `未找到匹配的用户`, and the case was rerun with that visible
  UI text.
- 后续：无。

## 边界

- Autonomous endpoints called: no.
- `/exploration/autonomous-runs` called: no.
- `/exploration/autonomous-runs/stream` called: no.
- Autonomous explorer imported or run directly: no.
- verify-scenario used: no.
- 产品侧 LLM provider used: no.
- Product code modified: no.
- E2E spec modified: no.
- Package scripts modified: no.
- `docs/iterations/` modified: no.

## 原始证据附录

### 仓库状态

```text
$ git rev-parse HEAD
818c30a564e2c2d61039f5ceb13f780c8a18e3dc

$ git status --short
<no output>
```

### 服务检查

```text
$ curl -sS -i http://127.0.0.1:8001/health
HTTP/1.1 200 OK
content-type: application/json

{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}

$ curl -sS -I https://example.invalid/entry
HTTP/1.1 200 OK
Content-Type: text/html

$ curl -sS -I https://example.invalid/records
HTTP/1.1 200 OK
Content-Type: text/html
```

### Browser observation 摘录

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
