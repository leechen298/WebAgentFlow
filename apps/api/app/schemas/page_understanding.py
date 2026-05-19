"""M11.3.5 page understanding schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PageVisibleControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str | None = None
    label: str | None = None
    category: str | None = None


class SupportedPageGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str
    canonical_goal: str | None = None
    aliases: list[str] = Field(default_factory=list)
    required_slots: list[str] = Field(default_factory=list)


class PageUnderstandingResult(BaseModel):
    """Semantic page summary for routing, not execution proof."""

    model_config = ConfigDict(extra="forbid")

    observed_page_summary: str
    visible_controls: list[PageVisibleControl] = Field(default_factory=list)
    page_context_summary: str | None = None
    supported_goals: list[SupportedPageGoal] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason_summary: str = ""
    source: str = "deterministic"

    @model_validator(mode="after")
    def _reject_execution_details(self) -> PageUnderstandingResult:
        payload_text = self.model_dump_json(exclude_none=True)
        forbidden = (
            "selector",
            "dom_path",
            "playwright",
            "browser_step",
            "learned_path_id",
        )
        lowered = payload_text.lower()
        for token in forbidden:
            if token in lowered:
                raise ValueError(f"page understanding output must not contain {token}")
        return self
