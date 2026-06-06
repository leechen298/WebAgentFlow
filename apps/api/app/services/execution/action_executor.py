"""Shared action executor.

Single-step browser action execution used by both autonomous exploration
and LearnedPath replay.  Keeps step-log field compatibility with the
original autonomous_explorer implementation.
"""

from __future__ import annotations

import time
from typing import Any

from app.services.execution.execution_runtime import ExecutionRuntime


def safe_screenshot(runtime: ExecutionRuntime) -> str | None:
    """Take a screenshot, return path or None on failure."""
    try:
        path = runtime.screenshot()
        if path:
            return path
    except Exception:
        pass
    try:
        return runtime.screenshot(full_page=False)
    except Exception:
        return None


def observe_step(runtime: ExecutionRuntime, step_index: int) -> dict[str, Any]:
    """Capture final page state without performing any action.

    Returns a step log dict with the same fields the autonomous pipeline
    expects (``ok``, ``url``, ``title``, ``result_signals``, ``screenshot_ref``).
    """
    page = runtime.page
    time.sleep(2.0)  # Wait for any pending navigation

    step_log: dict[str, Any] = {
        "step_index": step_index,
        "action_type": "observe",
        "ok": True,
    }

    if page and not page.is_closed():
        step_log["url"] = page.url
        step_log["title"] = page.title()

        # Discover elements on the result page to check for content
        try:
            result_signals = page.evaluate("""() => {
                const signals = {};

                function isPlaceholderRow(tr) {
                    const cls = (tr.className && tr.className.toString)
                        ? tr.className.toString() : '';
                    return cls.indexOf('placeholder') !== -1
                        || cls.indexOf('empty-row') !== -1;
                }

                let rowCount = 0;
                for (const tr of document.querySelectorAll('tbody tr')) {
                    if (tr.getAttribute('aria-hidden') === 'true') continue;
                    if (isPlaceholderRow(tr)) continue;
                    rowCount++;
                }
                for (const row of document.querySelectorAll('[role="row"]')) {
                    if (row.querySelector('[role="columnheader"]')) continue;
                    if (row.tagName === 'TR' && row.closest('tbody')) continue;
                    if (isPlaceholderRow(row)) continue;
                    rowCount++;
                }
                signals.result_row_count = rowCount;

                signals.has_captcha = !!(
                    document.title.match(/验证|captcha|challenge|security/i)
                    || document.URL.match(/captcha|verify|sorry|challenge/i)
                );
                signals.has_login_wall = !!(
                    document.title.match(/登录|login|sign.?in/i)
                    || document.querySelector('[class*=login-wall], [class*=login-modal]')
                );
                signals.visible_text_length = document.body
                    ? document.body.innerText.length : 0;
                return signals;
            }""")
            step_log["result_signals"] = result_signals
        except Exception:
            pass

    step_log["screenshot_ref"] = safe_screenshot(runtime)
    return step_log


def execute_action(action, runtime: ExecutionRuntime) -> dict[str, Any]:
    """Execute a single action and return the step log.

    *action* is any duck-typed object with at least ``step``,
    ``action_type``, ``target_selector``, ``target_description``,
    and ``value`` attributes.  Optional ``reason`` is also forwarded
    into the log when present.
    """
    page = runtime.page
    ts = int(time.time() * 1000)

    step_log: dict[str, Any] = {
        "step_index": action.step,
        "action_type": action.action_type,
        "target_selector": action.target_selector,
        "target_description": getattr(action, "target_description", None),
        "value": getattr(action, "value", None),
        "plan_reason": getattr(action, "reason", None),
        "timestamp_ms": ts,
    }

    if action.action_type == "observe":
        observe_log = observe_step(runtime, step_index=action.step)
        step_log.update(observe_log)
        return step_log

    if page is None or page.is_closed():
        step_log["ok"] = False
        step_log["error"] = "No page available"
        return step_log

    # Capture before state
    before_url = page.url
    before_title = page.title()

    try:
        locator = page.locator(action.target_selector)

        # Verify element exists
        count = locator.count()
        if count == 0:
            step_log["ok"] = False
            step_log["error"] = (
                f"Selector '{action.target_selector}' matched 0 elements"
            )
            step_log["screenshot_ref"] = safe_screenshot(runtime)
            return step_log

        step_log["matched_count"] = count

        if action.action_type == "fill":
            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.fill(action.value or "")
            time.sleep(0.5)
            step_log["ok"] = True
            step_log["actual_value"] = locator.first.input_value()

        elif action.action_type == "select":
            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.select_option(action.value or "")
            time.sleep(0.5)
            step_log["ok"] = True
            step_log["actual_value"] = locator.first.input_value()

        elif action.action_type == "set_value":
            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.evaluate(
                """(el, value) => {
                    const proto = el instanceof HTMLTextAreaElement
                        ? HTMLTextAreaElement.prototype
                        : HTMLInputElement.prototype;
                    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
                    if (descriptor && descriptor.set) {
                        descriptor.set.call(el, value);
                    } else {
                        el.value = value;
                    }
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }""",
                action.value or "",
            )
            time.sleep(0.5)
            step_log["ok"] = True
            step_log["actual_value"] = locator.first.input_value()

        elif action.action_type == "select_first_option":
            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.click()
            time.sleep(0.5)
            selected = page.evaluate(
                """() => {
                    function visible(el) {
                        const rect = el.getBoundingClientRect();
                        const style = getComputedStyle(el);
                        return rect.width > 0 && rect.height > 0
                            && style.display !== 'none'
                            && style.visibility !== 'hidden';
                    }
                    const options = Array.from(document.querySelectorAll(
                        '[role="option"], .ant-select-item-option'
                    )).filter((el) => {
                        const disabled = el.getAttribute('aria-disabled') === 'true'
                            || el.classList.contains('ant-select-item-option-disabled');
                        const selected = el.getAttribute('aria-selected') === 'true'
                            || el.classList.contains('ant-select-item-option-selected');
                        return visible(el) && !disabled && !selected;
                    });
                    const option = options[0];
                    if (!option) return { selected: false };
                    const text = (option.innerText || option.textContent || '').trim();
                    option.click();
                    return { selected: true, text };
                }"""
            )
            if not selected or not selected.get("selected"):
                step_log["ok"] = False
                step_log["error"] = "No selectable popup option was found"
                step_log["screenshot_ref"] = safe_screenshot(runtime)
                return step_log
            time.sleep(0.5)
            step_log["ok"] = True
            step_log["selected_option"] = selected

        elif action.action_type == "click":
            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.click()
            time.sleep(2.0)  # Wait for navigation / page change
            step_log["ok"] = True

        elif action.action_type == "press":
            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.press(action.value or "Enter")
            time.sleep(2.0)
            step_log["ok"] = True

        else:
            step_log["ok"] = False
            step_log["error"] = f"Unknown action type: {action.action_type}"
            return step_log

    except Exception as exc:
        step_log["ok"] = False
        step_log["error"] = str(exc)[:300]
        step_log["screenshot_ref"] = safe_screenshot(runtime)
        return step_log

    # Capture after state
    after_url = page.url
    after_title = page.title()
    step_log["url_before"] = before_url
    step_log["url_after"] = after_url
    step_log["title_before"] = before_title
    step_log["title_after"] = after_title
    step_log["url_changed"] = after_url != before_url
    step_log["title_changed"] = after_title != before_title
    step_log["screenshot_ref"] = safe_screenshot(runtime)

    return step_log
