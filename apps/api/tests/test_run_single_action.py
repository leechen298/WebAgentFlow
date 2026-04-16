"""
Tests for run_single_action module.

Covers:

_build_hints_from_task_hint:
1.  None input → empty list
2.  role hint → STRONG_ATTRIBUTE strategy with role=... value
3.  role + name → includes name in meta
4.  placeholder → STRONG_ATTRIBUTE strategy
5.  text → TAG_TEXT_LABEL strategy
6.  selector → FALLBACK_SELECTOR strategy
7.  Multiple hints from a single TaskStepHint with many fields
8.  name without role → TAG_TEXT_LABEL strategy (not STRONG_ATTRIBUTE)

run_single_action:
9.  Basic click action → calls execute_and_observe with correct ExecutionRequest
10. Fill action with value → value propagated
11. Navigate action → works without target_hint
12. Custom locator_hints override target_hint
13. Runtime.current_url / current_title called for page snapshot
14. Runtime.current_url raises → empty string fallback
15. Runtime.current_title raises → empty string fallback

All tests use mocks — no real Playwright, no real websites, no LLM calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.execution import (
    ExecutionRequest,
    ExecutionResult,
    LocatorHint,
)
from app.schemas.task_definition import TaskStepHint
from app.services.execution.run_single_action import (
    _build_hints_from_task_hint,
    run_single_action,
)


# ---------------------------------------------------------------------------
# _build_hints_from_task_hint
# ---------------------------------------------------------------------------


class TestBuildHintsFromTaskHint:
    """Tests for converting TaskStepHint into LocatorHint list."""

    def test_none_input_returns_empty_list(self):
        result = _build_hints_from_task_hint(None)
        assert result == []

    def test_role_hint_produces_strong_attribute(self):
        hint = TaskStepHint(role="button", tag="button")
        result = _build_hints_from_task_hint(hint)

        role_hints = [h for h in result if "role=" in h.value]
        assert len(role_hints) == 1
        h = role_hints[0]
        assert h.strategy == "STRONG_ATTRIBUTE"
        assert h.value == "role=button"
        assert h.confidence == "medium"
        assert h.meta.get("tag") == "button"

    def test_role_with_name_includes_name_in_meta(self):
        hint = TaskStepHint(role="textbox", name="Username", tag="input")
        result = _build_hints_from_task_hint(hint)

        role_hints = [h for h in result if h.value.startswith("role=")]
        assert len(role_hints) == 1
        h = role_hints[0]
        assert h.strategy == "STRONG_ATTRIBUTE"
        assert h.value == "role=textbox"
        assert h.meta.get("name") == "Username"
        assert h.meta.get("tag") == "input"

    def test_role_with_name_does_not_produce_separate_name_hint(self):
        """When role is present, name is folded into role meta, not a separate TAG_TEXT_LABEL."""
        hint = TaskStepHint(role="textbox", name="Username", tag="input")
        result = _build_hints_from_task_hint(hint)

        # There should be no TAG_TEXT_LABEL hint for name since role is set
        name_only_hints = [
            h for h in result
            if h.strategy == "TAG_TEXT_LABEL" and "Username" in h.value
        ]
        assert len(name_only_hints) == 0

    def test_placeholder_produces_strong_attribute(self):
        hint = TaskStepHint(placeholder="Enter your email", tag="input")
        result = _build_hints_from_task_hint(hint)

        ph_hints = [h for h in result if "placeholder=" in h.value]
        assert len(ph_hints) == 1
        h = ph_hints[0]
        assert h.strategy == "STRONG_ATTRIBUTE"
        assert h.value == "placeholder=Enter your email"
        assert h.confidence == "medium"

    def test_text_produces_tag_text_label(self):
        hint = TaskStepHint(text="Submit", tag="button")
        result = _build_hints_from_task_hint(hint)

        text_hints = [h for h in result if h.strategy == "TAG_TEXT_LABEL"]
        assert len(text_hints) == 1
        h = text_hints[0]
        assert h.value == "button::Submit"
        assert h.confidence == "medium"

    def test_text_without_tag_uses_wildcard(self):
        hint = TaskStepHint(text="Submit")
        result = _build_hints_from_task_hint(hint)

        text_hints = [h for h in result if h.strategy == "TAG_TEXT_LABEL"]
        assert len(text_hints) == 1
        assert text_hints[0].value == "*::Submit"

    def test_selector_produces_fallback_selector(self):
        hint = TaskStepHint(selector="#main-form .submit-btn", tag="button")
        result = _build_hints_from_task_hint(hint)

        sel_hints = [h for h in result if h.strategy == "FALLBACK_SELECTOR"]
        assert len(sel_hints) == 1
        h = sel_hints[0]
        assert h.value == "#main-form .submit-btn"
        assert h.confidence == "low"

    def test_name_without_role_produces_tag_text_label(self):
        """When name is set but role is not, name becomes TAG_TEXT_LABEL."""
        hint = TaskStepHint(name="search", tag="input")
        result = _build_hints_from_task_hint(hint)

        tag_text_hints = [h for h in result if h.strategy == "TAG_TEXT_LABEL"]
        assert len(tag_text_hints) == 1
        assert tag_text_hints[0].value == "input::search"

    def test_multiple_fields_produce_multiple_hints(self):
        """A TaskStepHint with many fields should produce multiple hints."""
        hint = TaskStepHint(
            role="combobox",
            name="City",
            tag="input",
            placeholder="Select city",
            text="Choose your city",
            selector=".city-selector input",
        )
        result = _build_hints_from_task_hint(hint)

        strategies = [h.strategy for h in result]

        # role → STRONG_ATTRIBUTE
        assert "STRONG_ATTRIBUTE" in strategies
        # placeholder → STRONG_ATTRIBUTE
        strong_attr_hints = [h for h in result if h.strategy == "STRONG_ATTRIBUTE"]
        assert len(strong_attr_hints) == 2  # role + placeholder

        # text → TAG_TEXT_LABEL
        assert "TAG_TEXT_LABEL" in strategies

        # selector → FALLBACK_SELECTOR
        assert "FALLBACK_SELECTOR" in strategies

        # At least 4 hints total (role, placeholder, text, selector)
        # name is folded into role meta, not a separate hint
        assert len(result) >= 4

    def test_empty_hint_returns_empty_list(self):
        """A TaskStepHint with all None fields produces no hints."""
        hint = TaskStepHint()
        result = _build_hints_from_task_hint(hint)
        assert result == []


# ---------------------------------------------------------------------------
# run_single_action
# ---------------------------------------------------------------------------


class TestRunSingleAction:
    """Tests for run_single_action using mocked runtime and execute_and_observe."""

    def _make_mock_runtime(
        self, url: str = "https://example.com", title: str = "Example"
    ) -> MagicMock:
        runtime = MagicMock(spec=["current_url", "current_title"])
        runtime.current_url.return_value = url
        runtime.current_title.return_value = title
        return runtime

    def _make_result(self, **overrides) -> ExecutionResult:
        defaults = dict(ok=True, action_type="click", target_summary="button")
        defaults.update(overrides)
        return ExecutionResult(**defaults)

    @patch(
        "app.services.execution.post_action_observer.execute_and_observe",
    )
    def test_basic_click_action(self, mock_eao):
        """Click action assembles correct ExecutionRequest and returns result."""
        expected = self._make_result(action_type="click")
        mock_eao.return_value = expected
        runtime = self._make_mock_runtime()

        result = run_single_action(
            action_type="click",
            runtime=runtime,
            target_description='<button> "Save"',
            target_hint=TaskStepHint(role="button", tag="button"),
        )

        assert result is expected
        mock_eao.assert_called_once()

        # Inspect the ExecutionRequest passed to execute_and_observe
        call_args = mock_eao.call_args
        request = call_args[0][0]
        assert isinstance(request, ExecutionRequest)
        assert request.action.action_type == "click"
        assert request.action.target_description == '<button> "Save"'
        assert request.action.value is None
        assert request.page.url == "https://example.com"
        assert request.page.title == "Example"
        assert len(request.locator_hints) > 0
        # role hint should be present
        assert any(h.value == "role=button" for h in request.locator_hints)

    @patch(
        "app.services.execution.post_action_observer.execute_and_observe",
    )
    def test_fill_action_propagates_value(self, mock_eao):
        """Fill action passes value through to the ExecutionRequest."""
        expected = self._make_result(action_type="fill")
        mock_eao.return_value = expected
        runtime = self._make_mock_runtime()

        result = run_single_action(
            action_type="fill",
            runtime=runtime,
            target_description='<input> "Username"',
            value="alice",
            target_hint=TaskStepHint(placeholder="Enter username", tag="input"),
        )

        assert result is expected
        request = mock_eao.call_args[0][0]
        assert request.action.action_type == "fill"
        assert request.action.value == "alice"

    @patch(
        "app.services.execution.post_action_observer.execute_and_observe",
    )
    def test_navigate_action_without_target_hint(self, mock_eao):
        """Navigate action works with no target_hint (produces empty hints)."""
        expected = self._make_result(action_type="navigate")
        mock_eao.return_value = expected
        runtime = self._make_mock_runtime()

        result = run_single_action(
            action_type="navigate",
            runtime=runtime,
            target_description="Go to settings page",
            value="https://example.com/settings",
        )

        assert result is expected
        request = mock_eao.call_args[0][0]
        assert request.action.action_type == "navigate"
        assert request.action.value == "https://example.com/settings"
        assert request.locator_hints == []

    @patch(
        "app.services.execution.post_action_observer.execute_and_observe",
    )
    def test_custom_locator_hints_override_target_hint(self, mock_eao):
        """When locator_hints is provided, target_hint is ignored."""
        expected = self._make_result()
        mock_eao.return_value = expected
        runtime = self._make_mock_runtime()

        custom_hints = [
            LocatorHint(
                strategy="STRONG_ATTRIBUTE",
                value="id=my-button",
                confidence="high",
                meta={"attribute": "id"},
            ),
        ]

        result = run_single_action(
            action_type="click",
            runtime=runtime,
            target_description="My button",
            target_hint=TaskStepHint(role="button", text="Something else"),
            locator_hints=custom_hints,
        )

        assert result is expected
        request = mock_eao.call_args[0][0]
        # Should use the custom hints, not hints derived from target_hint
        assert len(request.locator_hints) == 1
        assert request.locator_hints[0].value == "id=my-button"
        assert request.locator_hints[0].confidence == "high"

    @patch(
        "app.services.execution.post_action_observer.execute_and_observe",
    )
    def test_runtime_current_url_and_title_called(self, mock_eao):
        """Runtime's current_url and current_title are called for page snapshot."""
        expected = self._make_result()
        mock_eao.return_value = expected
        runtime = self._make_mock_runtime(
            url="https://test.dev/page", title="Test Page"
        )

        run_single_action(
            action_type="click",
            runtime=runtime,
            target_description="a button",
        )

        runtime.current_url.assert_called_once()
        runtime.current_title.assert_called_once()

        request = mock_eao.call_args[0][0]
        assert request.page.url == "https://test.dev/page"
        assert request.page.title == "Test Page"

    @patch(
        "app.services.execution.post_action_observer.execute_and_observe",
    )
    def test_runtime_current_url_failure_falls_back_to_empty(self, mock_eao):
        """If runtime.current_url() raises, url defaults to empty string."""
        expected = self._make_result()
        mock_eao.return_value = expected
        runtime = self._make_mock_runtime()
        runtime.current_url.side_effect = RuntimeError("page closed")

        run_single_action(
            action_type="click",
            runtime=runtime,
            target_description="a button",
        )

        request = mock_eao.call_args[0][0]
        assert request.page.url == ""

    @patch(
        "app.services.execution.post_action_observer.execute_and_observe",
    )
    def test_runtime_current_title_failure_falls_back_to_empty(self, mock_eao):
        """If runtime.current_title() raises, title defaults to empty string."""
        expected = self._make_result()
        mock_eao.return_value = expected
        runtime = self._make_mock_runtime()
        runtime.current_title.side_effect = RuntimeError("page closed")

        run_single_action(
            action_type="click",
            runtime=runtime,
            target_description="a button",
        )

        request = mock_eao.call_args[0][0]
        assert request.page.title == ""

    @patch(
        "app.services.execution.post_action_observer.execute_and_observe",
    )
    def test_region_constraint_propagated(self, mock_eao):
        """region_constraint is forwarded to ActionTarget."""
        expected = self._make_result()
        mock_eao.return_value = expected
        runtime = self._make_mock_runtime()

        run_single_action(
            action_type="click",
            runtime=runtime,
            target_description="Submit in form",
            region_constraint="main-form",
        )

        request = mock_eao.call_args[0][0]
        assert request.action.region_constraint == "main-form"

    @patch(
        "app.services.execution.post_action_observer.execute_and_observe",
    )
    def test_understanding_is_empty_dict(self, mock_eao):
        """ExecutionRequest.understanding is always empty dict from this entry point."""
        expected = self._make_result()
        mock_eao.return_value = expected
        runtime = self._make_mock_runtime()

        run_single_action(
            action_type="click",
            runtime=runtime,
            target_description="btn",
        )

        request = mock_eao.call_args[0][0]
        assert request.understanding == {}

    @patch(
        "app.services.execution.post_action_observer.execute_and_observe",
    )
    def test_execute_and_observe_receives_runtime(self, mock_eao):
        """The runtime object is passed as the second argument to execute_and_observe."""
        expected = self._make_result()
        mock_eao.return_value = expected
        runtime = self._make_mock_runtime()

        run_single_action(
            action_type="hover",
            runtime=runtime,
            target_description="menu item",
        )

        call_args = mock_eao.call_args
        assert call_args[0][1] is runtime
