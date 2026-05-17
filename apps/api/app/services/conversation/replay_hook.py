"""Explicit replay command hook for M11.0.6.

Bridges the Orchestrator's `/replay` command to the M10 replay engine.
No path selection, no slot binding, no LLM, no autonomous runs.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from app.models.learned_path import TrustStatus
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.conversation import ConversationReplaySummary
from app.services.learning.learned_path_replay import run_replay


class ReplayHandler(Protocol):
    """Callable that runs an explicit replay and returns a summary."""

    def __call__(
        self, learned_path_id: str, url: str, *, headless: bool = True
    ) -> ConversationReplaySummary:
        ...


def run_explicit_replay(
    db_session: Session,
    learned_path_id: str,
    url: str,
    *,
    headless: bool = True,
) -> ConversationReplaySummary:
    """Look up a LearnedPath and run M10 replay against *url*.

    Returns a ``ConversationReplaySummary`` regardless of outcome.
    """
    path_repo = LearnedPathRepository(db_session)
    learned_path = path_repo.get(learned_path_id)

    if learned_path is None:
        return ConversationReplaySummary(
            learned_path_id=learned_path_id,
            url=url,
            replay_status="candidate_not_found",
            drift_status="no_candidate",
            error="LearnedPath not found",
        )

    if learned_path.trust == TrustStatus.DEPRECATED:
        return ConversationReplaySummary(
            learned_path_id=learned_path_id,
            url=url,
            replay_status="deprecated",
            drift_status="none",
            error="LearnedPath is deprecated",
        )

    result = run_replay(learned_path, url, headless=headless)

    return ConversationReplaySummary(
        learned_path_id=result.learned_path_id,
        url=url,
        replay_status=result.status,
        drift_status=result.drift_status,
        drift_reasons=result.drift_reasons,
        warnings=result.warnings,
        final_url=result.final_url,
        final_title=result.final_title,
        step_count=len(result.steps),
        error=None,
    )
