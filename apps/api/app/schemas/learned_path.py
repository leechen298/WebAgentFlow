"""Pydantic schemas for the LearnedPath HTTP surface.

Shape choices:

- ``LearnedPathSummary`` is the list-row projection — no ``actions``,
  which can be large. The detail endpoint returns the full
  ``LearnedPathDetail`` with actions included.
- ``TrustPatchRequest`` restricts ``status`` to the three
  user-reachable targets (``confirmed``/``deprecated``/``flaky``);
  the initial ``provisional`` state is only written by the ingest
  hook, never by the PATCH route.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LearnedPathSummary(BaseModel):
    id: str
    page_template: str
    query_signature: dict[str, str]
    dom_fingerprint: str
    scenario: str
    provenance: str
    trust: str
    trust_reason: str | None = None
    trust_updated_at: datetime | None = None
    hit_count: int
    source_run_id: str | None = None
    created_at: datetime
    updated_at: datetime


class LearnedPathDetail(LearnedPathSummary):
    actions: list[dict[str, Any]] = Field(default_factory=list)


class TrustPatchRequest(BaseModel):
    status: Literal["confirmed", "deprecated", "flaky"]
    reason: str | None = Field(default=None, max_length=500)
