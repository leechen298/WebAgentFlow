# Page Verification Spec · Login

**Location**: `apps/validation-site/src/pages/LoginPage.vue`
**Route**: `/login`
**Backend**: `POST /validation-api/login`

This document is the authored baseline for autonomous exploration against
the login page. It is NOT derived from any autonomous-run output.

---

## 1. Page Goal

Let a user authenticate by entering credentials and pressing the submit
button. On success the user is routed to `/dashboard`; on failure the
page stays at `/login` and surfaces an error message in a persistent
alert region.

This is the simplest closed-loop page in the validation suite:
**fill → fill → submit → (dashboard or alert)**.

## 2. Key Regions

| Region | DOM | Notes |
|---|---|---|
| Username input | `<input id="username" name="username" type="text">` | Primary fillable |
| Password input | `<input id="password" name="password" type="password">` | Primary fillable, obscured input |
| Submit button | `<button type="submit">Sign in</button>` | Inside the `<form>`; HTML default behavior submits the form |
| Error alert | `<div role="alert" data-testid="login-error">` | Only mounted after a failed submit (`v-if="errorMessage"`). Verified via `failure_signals` in the assertions JSON, **not** as a `critical_element` — page analysis runs before any action, so this region doesn't exist yet at analysis time. |
| Secondary link — Forgot password | `<a href="#forgot">Forgot password?</a>` | Distraction |
| Secondary link — Contact admin | `<a href="#contact">Contact admin</a>` | Distraction |

## 3. Key Actions

The correct action path is exactly three steps, order-insensitive for
the two fill actions but submit must come last:

1. **fill** username
2. **fill** password
3. **click** submit

The page does not require pressing Enter — there is an explicit submit
button inside a `<form>`. Pressing Enter inside either input would also
submit, but clicking the button is the canonical path.

## 4. Success Criteria

All of:

- Navigation transitions away from `/login` to `/dashboard`
- `document.title` changes to contain `"Dashboard"`
- DOM contains both strings: `"Welcome"` and `"Validation Site — Dashboard"` (the exact page header)
- DOM contains the structural marker `data-testid="dashboard-welcome"`
- No `role="alert"` element is visible on the final page

## 5. Failure Criteria

All of:

- Navigation stays on `/login` (URL does NOT transition to `/dashboard`)
- A `role="alert"` element appears and is visible on the final page
- Alert text is the authoritative backend copy `用户名或密码错误` (no generic words like "Invalid" or "failed" — this is a self-hosted fixture so the text is deterministic)
- `document.title` does NOT change to contain `"Dashboard"`

A run that is reported as success but final URL is `/login`, or a run
reported as failure but final URL is `/dashboard`, is a verdict error.

## 6. Distractions

These elements must be **present on the page** but must **not be chosen
as the primary submit action**. If WebAgentFlow ever clicks one of these
during a login attempt, it is a distraction-avoidance failure.

- `<a href="#forgot">Forgot password?</a>`
- `<a href="#contact">Contact admin</a>`

## 7. Expected Coverage Scope

Phase 1 of this spec only enforces:

1. **Success scenario** — correct credentials (`admin` / `123456`)
2. **Failure scenario** — incorrect credentials (anything else)

Out of scope in Phase 1:

- Empty-field submission handling
- Server-down / network-failure handling
- Keyboard-only submission (Enter key)
- Autocomplete behavior
- Accessibility attributes beyond `role="alert"`

---

## Notes for the Spec Author

- This spec was written **before** any autonomous exploration run
  against the login page. Do not patch the spec to match observed system
  behavior — patch the system instead.
- The machine-readable equivalent lives in `login.assertions.json`. If
  the two diverge, the JSON is the source of truth for the comparator;
  this Markdown is the narrative for humans.
