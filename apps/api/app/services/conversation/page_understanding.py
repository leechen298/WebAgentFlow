"""Page Understanding Agent runtime for M11.3.5."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.schemas.page_understanding import (
    PageUnderstandingResult,
    PageVisibleControl,
    SupportedPageGoal,
)
from app.services.conversation.intake import redact_sensitive_payload
from app.services.conversation.page_context import PageContextBundle

PageUnderstandingProvider = Callable[
    [dict[str, Any]], PageUnderstandingResult | dict[str, Any] | None
]


class PageUnderstandingService:
    def __init__(
        self,
        provider: PageUnderstandingProvider | None = None,
        *,
        confidence_threshold: float = 0.6,
    ) -> None:
        self._provider = provider
        self.confidence_threshold = confidence_threshold
        self.provider_fallback = False

    def understand(self, context: PageContextBundle) -> PageUnderstandingResult:
        self.provider_fallback = False
        payload = redact_sensitive_payload(context.model_dump(mode="json"))
        if self._provider is not None:
            try:
                provided = self._provider(payload)
                if provided is not None:
                    result = (
                        provided
                        if isinstance(provided, PageUnderstandingResult)
                        else PageUnderstandingResult.model_validate(provided)
                    )
                    return result
                self.provider_fallback = True
            except (TypeError, ValidationError, ValueError):
                return PageUnderstandingResult(
                    observed_page_summary="Page understanding output was invalid.",
                    confidence=0.0,
                    reason_summary="provider output failed schema validation",
                    source="provider_error",
                )
        return deterministic_page_understanding(context)


def deterministic_page_understanding(
    context: PageContextBundle,
) -> PageUnderstandingResult:
    controls = [
        PageVisibleControl(
            role=item.get("role") or item.get("semantic_role"),
            label=item.get("label"),
            category=item.get("category"),
        )
        for item in context.interactive_elements
    ]
    labels = {
        str(control.label).lower()
        for control in controls
        if control.label is not None
    }
    required_slots: list[str] = []
    if any("password" in label or "密码" in label or "口令" in label for label in labels):
        required_slots.append("password")
    if any("username" in label or "账号" in label or "用户" in label for label in labels):
        required_slots.append("username")
    goal_label = "operate page"
    if "username" in required_slots and "password" in required_slots:
        goal_label = "login"

    return PageUnderstandingResult(
        observed_page_summary=(
            f"{context.title or context.url} exposes "
            f"{len(context.interactive_elements)} visible interactive controls."
        ),
        visible_controls=controls,
        page_context_summary=context.visible_text_summary,
        supported_goals=[
            SupportedPageGoal(
                goal=goal_label,
                canonical_goal=goal_label,
                aliases=[goal_label],
                required_slots=required_slots,
            )
        ],
        confidence=0.7 if controls else 0.45,
        reason_summary="deterministic summary from page context bundle",
        source="deterministic",
    )
