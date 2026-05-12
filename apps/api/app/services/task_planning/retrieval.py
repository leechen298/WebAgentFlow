"""Deterministic LearnedPath retrieval and ranking for task planning.

This module provides the first-layer candidate search used by the Task Path
Planner (11.1.2).  It is a pure code-side service: no LLM, no replay, no
autonomous exploration, no raw HTML analysis.

Ranking score is an internal implementation detail; the public contract
expressed through ``LearnedPathCandidate.match_reasons`` and
``.warnings``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.learned_path import LearnedPath, TrustStatus
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.task_planning import LearnedPathCandidate, TaskIntent

# ---------------------------------------------------------------------------
# Internal ranking types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _RankedCandidate:
    """Internal pairing of a public candidate with its deterministic score.

    ``score`` is *not* exposed on ``LearnedPathCandidate`` in 11.1.2;
    it exists only for stable sorting and testability.
    """

    candidate: LearnedPathCandidate
    score: float
    score_reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Score constants (documented so the formula stays deterministic and auditable)
# ---------------------------------------------------------------------------

_SCENARIO_EXACT_MATCH = 50.0
_PAGE_TEMPLATE_EXACT_MATCH = 30.0
_PAGE_TEMPLATE_CONTAINS_MATCH = 15.0
_TRUST_CONFIRMED = 20.0
_TRUST_PROVISIONAL = 10.0
_TRUST_FLAKY = 0.0
_TRUST_DEPRECATED = -100.0
_HIT_COUNT_CAP = 10
_KEYWORD_OVERLAP_PER_TOKEN = 2.0

_LIMIT_DEFAULT = 10
_LIMIT_MIN = 1
_LIMIT_MAX = 50


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


def _tokenize(text: str | None) -> set[str]:
    """Deterministic lowercase token extraction.

    Splits on non-alphanumeric boundaries.  CJK characters are treated as
    individual tokens so that ``登录`` becomes ``{"登", "录"}``.
    """
    if not text:
        return set()
    lowered = text.lower()
    # Split on sequences that are *not* word characters.
    tokens = re.split(r"[^\w]", lowered)
    return {t for t in tokens if t}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class LearnedPathRetrievalService:
    """Retrieve and rank ``LearnedPathCandidate`` rows for a ``TaskIntent``."""

    def __init__(self, repo: LearnedPathRepository) -> None:
        self._repo = repo

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve_candidates(
        self,
        task_intent: TaskIntent,
        *,
        limit: int = _LIMIT_DEFAULT,
    ) -> list[LearnedPathCandidate]:
        """Return ranked ``LearnedPathCandidate`` objects for *task_intent*.

        ``deprecated`` paths are excluded by default.  ``limit`` is clamped
        to ``[1, 50]``.  If no paths exist an empty list is returned.
        """
        limit = max(_LIMIT_MIN, min(limit, _LIMIT_MAX))

        paths = self._repo.list_candidates()
        if not paths:
            return []

        ranked = [self._score_path(task_intent, path) for path in paths]
        ranked.sort(key=lambda rc: rc.score, reverse=True)

        return [rc.candidate for rc in ranked[:limit]]

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_path(
        self,
        task_intent: TaskIntent,
        path: LearnedPath,
    ) -> _RankedCandidate:
        score = 0.0
        reasons: list[str] = []
        warnings: list[str] = []
        score_reasons: list[str] = []

        # --- trust base score ------------------------------------------------
        trust = TrustStatus(path.trust)
        if trust == TrustStatus.CONFIRMED:
            score += _TRUST_CONFIRMED
            reasons.append("Trust level: confirmed")
            score_reasons.append(f"trust=confirmed (+{_TRUST_CONFIRMED})")
        elif trust == TrustStatus.PROVISIONAL:
            score += _TRUST_PROVISIONAL
            reasons.append("Trust level: provisional")
            score_reasons.append(f"trust=provisional (+{_TRUST_PROVISIONAL})")
        elif trust == TrustStatus.FLAKY:
            score += _TRUST_FLAKY
            reasons.append("Trust level: flaky")
            score_reasons.append(f"trust=flaky (+{_TRUST_FLAKY})")
            warnings.append("Trust level is flaky; result may be unstable")
        else:
            score += _TRUST_DEPRECATED
            score_reasons.append(f"trust=deprecated (+{_TRUST_DEPRECATED})")
            # deprecated paths should have been filtered by list_candidates,
            # but we keep the math consistent.

        # --- hit count -------------------------------------------------------
        hit_bonus = min(path.hit_count or 0, _HIT_COUNT_CAP)
        if hit_bonus:
            score += hit_bonus
            reasons.append(f"Hit count: {path.hit_count}")
            score_reasons.append(f"hit_count={path.hit_count} (capped at +{hit_bonus})")

        # --- scenario match --------------------------------------------------
        scenario_hint = (task_intent.scenario_hint or "").strip()
        if scenario_hint and scenario_hint.lower() == (path.scenario or "").lower():
            score += _SCENARIO_EXACT_MATCH
            reasons.append(f"Exact scenario match: {path.scenario}")
            score_reasons.append(
                f"scenario exact match (+{_SCENARIO_EXACT_MATCH})"
            )

        # --- page template match ---------------------------------------------
        page_hint = (task_intent.target_page_hint or "").strip()
        path_page = (path.page_template or "").strip()
        if page_hint and path_page:
            if page_hint.lower() == path_page.lower():
                score += _PAGE_TEMPLATE_EXACT_MATCH
                reasons.append(f"Exact page template match: {path_page}")
                score_reasons.append(
                    f"page_template exact match (+{_PAGE_TEMPLATE_EXACT_MATCH})"
                )
            elif page_hint.lower() in path_page.lower():
                score += _PAGE_TEMPLATE_CONTAINS_MATCH
                reasons.append(f"Page template contains hint: {path_page}")
                score_reasons.append(
                    f"page_template contains match (+{_PAGE_TEMPLATE_CONTAINS_MATCH})"
                )
            elif path_page.lower() in page_hint.lower():
                score += _PAGE_TEMPLATE_CONTAINS_MATCH
                reasons.append(f"Page template contained in hint: {path_page}")
                score_reasons.append(
                    f"page_template contained in hint (+{_PAGE_TEMPLATE_CONTAINS_MATCH})"
                )

        # --- keyword overlap -------------------------------------------------
        query_tokens: set[str] = set()
        query_tokens |= _tokenize(task_intent.raw_text)
        query_tokens |= _tokenize(task_intent.normalized_goal)
        query_tokens |= _tokenize(task_intent.scenario_hint)
        query_tokens |= _tokenize(task_intent.target_page_hint)

        path_tokens: set[str] = set()
        path_tokens |= _tokenize(path.scenario)
        path_tokens |= _tokenize(path.page_template)

        overlap = query_tokens & path_tokens
        if overlap:
            overlap_score = len(overlap) * _KEYWORD_OVERLAP_PER_TOKEN
            score += overlap_score
            reasons.append(f"Keyword overlap: {', '.join(sorted(overlap))}")
            score_reasons.append(
                f"keyword overlap {len(overlap)} tokens (+{overlap_score})"
            )

        # --- drift / negative evidence (conservative) ------------------------
        drift_summary: str | None = None
        negative_summary: str | None = None

        if path.trust_reason:
            # trust_reason is the only stable source available in 11.1.2.
            # We surface it as drift evidence when trust is not confirmed.
            if trust != TrustStatus.CONFIRMED:
                drift_summary = path.trust_reason
                warnings.append(f"Drift evidence: {path.trust_reason}")

        # negative_evidence_summary stays None in 11.1.2 (no negative store).

        candidate = LearnedPathCandidate(
            learned_path_id=str(path.id),
            scenario=path.scenario or "",
            page_template=path.page_template or "",
            trust=trust.value,  # type: ignore[arg-type]
            hit_count=path.hit_count or 0,
            match_reasons=reasons,
            warnings=warnings,
            drift_evidence_summary=drift_summary,
            negative_evidence_summary=negative_summary,
        )

        return _RankedCandidate(
            candidate=candidate,
            score=score,
            score_reasons=score_reasons,
        )
