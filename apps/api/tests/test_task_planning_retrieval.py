"""Tests for M11.1.2 LearnedPath retrieval and deterministic ranking.

These tests verify the retrieval service contract without exercising
LLM, replay, autonomous exploration, or slot binding.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.learned_path import LearnedPath, Provenance, TrustStatus
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.task_planning import TaskIntent
from app.services.task_planning.retrieval import (
    LearnedPathRetrievalService,
    _cjk_substring_overlap,
    _tokenize,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(db_session: Session) -> LearnedPathRepository:
    return LearnedPathRepository(db_session)


@pytest.fixture
def service(repo: LearnedPathRepository) -> LearnedPathRetrievalService:
    return LearnedPathRetrievalService(repo)


_COUNTER = 0


def _make_path(
    repo: LearnedPathRepository,
    *,
    page_template: str = "/users",
    query_signature: dict[str, str] | None = None,
    dom_fingerprint: str | None = None,
    scenario: str = "users-export",
    actions: list[dict] | None = None,
    trust: TrustStatus = TrustStatus.PROVISIONAL,
    trust_reason: str | None = None,
    hit_count: int = 1,
    source_run_id: str | None = None,
) -> LearnedPath:
    """Helper to persist a LearnedPath directly (bypassing dedup hit_count logic).

    ``dom_fingerprint`` is auto- uniquified so multiple calls with the same
    ``page_template`` and ``scenario`` do not collide on the dedup key.
    """
    from app.repos.learned_paths_repo import compute_dedup_key

    global _COUNTER
    _COUNTER += 1
    df = dom_fingerprint or f"abc{_COUNTER:04d}"

    qs = query_signature or {}
    acts = actions or []
    row = LearnedPath(
        page_template=page_template,
        query_signature=qs,
        dom_fingerprint=df,
        scenario=scenario,
        actions=acts,
        provenance=Provenance.SYSTEM,
        trust=trust,
        trust_reason=trust_reason,
        hit_count=hit_count,
        source_run_id=source_run_id,
        dedup_key=compute_dedup_key(
            page_template=page_template,
            query_signature=qs,
            dom_fingerprint=df,
            scenario=scenario,
        ),
    )
    repo.session.add(row)
    repo.session.commit()
    repo.session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Empty-catalog behaviour
# ---------------------------------------------------------------------------


def test_returns_empty_list_when_no_paths_exist(
    service: LearnedPathRetrievalService,
) -> None:
    intent = TaskIntent(raw_text="export users")
    candidates = service.retrieve_candidates(intent)
    assert candidates == []


# ---------------------------------------------------------------------------
# Trust filtering
# ---------------------------------------------------------------------------


def test_excludes_deprecated_by_default(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(repo, scenario="login", trust=TrustStatus.DEPRECATED)
    intent = TaskIntent(raw_text="login")
    candidates = service.retrieve_candidates(intent)
    assert candidates == []


def test_includes_confirmed_provisional_and_flaky(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    confirmed = _make_path(repo, scenario="login", trust=TrustStatus.CONFIRMED)
    provisional = _make_path(repo, scenario="login", trust=TrustStatus.PROVISIONAL)
    flaky = _make_path(repo, scenario="login", trust=TrustStatus.FLAKY)

    intent = TaskIntent(raw_text="login")
    candidates = service.retrieve_candidates(intent)
    ids = {c.learned_path_id for c in candidates}

    assert str(confirmed.id) in ids
    assert str(provisional.id) in ids
    assert str(flaky.id) in ids


def test_flaky_gets_warning(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(repo, scenario="login", trust=TrustStatus.FLAKY)
    intent = TaskIntent(raw_text="login")
    candidates = service.retrieve_candidates(intent)
    assert len(candidates) == 1
    assert any("flaky" in w.lower() for w in candidates[0].warnings)


# ---------------------------------------------------------------------------
# Ranking — trust precedence
# ---------------------------------------------------------------------------


def test_confirmed_outranks_provisional_when_other_signals_equal(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    confirmed = _make_path(
        repo, scenario="export", trust=TrustStatus.CONFIRMED, hit_count=1
    )
    provisional = _make_path(
        repo, scenario="export", trust=TrustStatus.PROVISIONAL, hit_count=1
    )

    intent = TaskIntent(raw_text="export users")
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].learned_path_id == str(confirmed.id)
    assert candidates[1].learned_path_id == str(provisional.id)


def test_provisional_outranks_flaky_when_other_signals_equal(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    provisional = _make_path(
        repo, scenario="export", trust=TrustStatus.PROVISIONAL, hit_count=1
    )
    flaky = _make_path(repo, scenario="export", trust=TrustStatus.FLAKY, hit_count=1)

    intent = TaskIntent(raw_text="export users")
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].learned_path_id == str(provisional.id)
    assert candidates[1].learned_path_id == str(flaky.id)


# ---------------------------------------------------------------------------
# Ranking — scenario hint
# ---------------------------------------------------------------------------


def test_exact_scenario_hint_match_ranks_first(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    exact = _make_path(repo, scenario="users-export", trust=TrustStatus.PROVISIONAL)
    other = _make_path(repo, scenario="orders-export", trust=TrustStatus.PROVISIONAL)

    intent = TaskIntent(raw_text="export users", scenario_hint="users-export")
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].learned_path_id == str(exact.id)
    assert candidates[1].learned_path_id == str(other.id)
    assert any("Exact scenario match" in r for r in candidates[0].match_reasons)


# ---------------------------------------------------------------------------
# Ranking — page template hint
# ---------------------------------------------------------------------------


def test_exact_page_template_match_contributes_to_score(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    exact = _make_path(
        repo, scenario="x", page_template="/users", trust=TrustStatus.PROVISIONAL
    )
    _make_path(
        repo, scenario="x", page_template="/orders", trust=TrustStatus.PROVISIONAL
    )

    intent = TaskIntent(
        raw_text="do something", target_page_hint="/users", scenario_hint="x"
    )
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].learned_path_id == str(exact.id)
    assert any("Exact page template match" in r for r in candidates[0].match_reasons)


def test_page_template_contains_match_contributes(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    contains = _make_path(
        repo,
        scenario="x",
        page_template="/admin/users/list",
        trust=TrustStatus.PROVISIONAL,
    )
    _make_path(
        repo, scenario="x", page_template="/orders", trust=TrustStatus.PROVISIONAL
    )

    intent = TaskIntent(
        raw_text="do something", target_page_hint="users", scenario_hint="x"
    )
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].learned_path_id == str(contains.id)
    assert any("contains" in r.lower() for r in candidates[0].match_reasons)


def test_empty_page_hint_does_not_exclude_candidate(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(repo, scenario="export", page_template="/users")
    intent = TaskIntent(raw_text="export users")
    candidates = service.retrieve_candidates(intent)
    assert len(candidates) == 1


# ---------------------------------------------------------------------------
# Ranking — hit_count
# ---------------------------------------------------------------------------


def test_hit_count_contributes_but_does_not_allow_deprecated_to_win(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(
        repo, scenario="login", trust=TrustStatus.DEPRECATED, hit_count=999
    )
    confirmed = _make_path(
        repo, scenario="login", trust=TrustStatus.CONFIRMED, hit_count=1
    )

    intent = TaskIntent(raw_text="login")
    candidates = service.retrieve_candidates(intent)
    assert len(candidates) == 1
    assert candidates[0].learned_path_id == str(confirmed.id)


def test_hit_count_boosts_score_within_cap(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    low_hits = _make_path(
        repo, scenario="export", trust=TrustStatus.PROVISIONAL, hit_count=1
    )
    high_hits = _make_path(
        repo, scenario="export", trust=TrustStatus.PROVISIONAL, hit_count=5
    )

    intent = TaskIntent(raw_text="export users")
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].learned_path_id == str(high_hits.id)
    assert candidates[1].learned_path_id == str(low_hits.id)


# ---------------------------------------------------------------------------
# Ranking — keyword overlap
# ---------------------------------------------------------------------------


def test_keyword_overlap_contributes_deterministic_score(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    matching = _make_path(
        repo, scenario="users-export", page_template="/users", trust=TrustStatus.PROVISIONAL
    )
    non_matching = _make_path(
        repo, scenario="orders-archive", page_template="/orders", trust=TrustStatus.PROVISIONAL
    )

    intent = TaskIntent(raw_text="export users")
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].learned_path_id == str(matching.id)
    assert candidates[1].learned_path_id == str(non_matching.id)
    assert any("Keyword overlap" in r for r in candidates[0].match_reasons)


# ---------------------------------------------------------------------------
# Limit clamping
# ---------------------------------------------------------------------------


def test_limit_defaults_to_ten(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    for i in range(15):
        _make_path(repo, scenario=f"task-{i}")

    intent = TaskIntent(raw_text="task")
    candidates = service.retrieve_candidates(intent)
    assert len(candidates) == 10


def test_limit_clamps_to_minimum_one(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(repo, scenario="login")
    _make_path(repo, scenario="login")

    intent = TaskIntent(raw_text="login")
    candidates = service.retrieve_candidates(intent, limit=0)
    assert len(candidates) == 1


def test_limit_clamps_to_maximum_fifty(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    for i in range(55):
        _make_path(repo, scenario=f"task-{i}")

    intent = TaskIntent(raw_text="task")
    candidates = service.retrieve_candidates(intent, limit=100)
    assert len(candidates) == 50


# ---------------------------------------------------------------------------
# Score stays internal
# ---------------------------------------------------------------------------


def test_score_is_not_a_public_field_on_candidate(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(repo, scenario="login", trust=TrustStatus.CONFIRMED)
    intent = TaskIntent(raw_text="login")
    candidates = service.retrieve_candidates(intent)
    assert len(candidates) == 1
    assert "score" not in type(candidates[0]).model_fields


# ---------------------------------------------------------------------------
# Match reasons & warnings population
# ---------------------------------------------------------------------------


def test_match_reasons_populated(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(repo, scenario="login", trust=TrustStatus.CONFIRMED, hit_count=3)
    intent = TaskIntent(raw_text="login", scenario_hint="login")
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].match_reasons
    assert any("Trust level" in r for r in candidates[0].match_reasons)
    assert any("Hit count" in r for r in candidates[0].match_reasons)
    assert any("Exact scenario match" in r for r in candidates[0].match_reasons)


def test_warnings_populated_for_flaky(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(repo, scenario="login", trust=TrustStatus.FLAKY)
    intent = TaskIntent(raw_text="login")
    candidates = service.retrieve_candidates(intent)
    assert any("flaky" in w.lower() for w in candidates[0].warnings)


def test_drift_summary_conservative_from_trust_reason(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(
        repo,
        scenario="login",
        trust=TrustStatus.FLAKY,
        trust_reason="button selector changed",
    )
    intent = TaskIntent(raw_text="login")
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].drift_evidence_summary == "button selector changed"
    assert any("Drift evidence" in w for w in candidates[0].warnings)


def test_negative_evidence_summary_empty_in_first_version(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(repo, scenario="login", trust=TrustStatus.CONFIRMED)
    intent = TaskIntent(raw_text="login")
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].negative_evidence_summary is None


# ---------------------------------------------------------------------------
# No hidden side effects
# ---------------------------------------------------------------------------


def test_does_not_mutate_trust_or_hit_count(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    path = _make_path(
        repo, scenario="login", trust=TrustStatus.PROVISIONAL, hit_count=5
    )
    original_trust = path.trust
    original_hits = path.hit_count

    intent = TaskIntent(raw_text="login")
    service.retrieve_candidates(intent)

    refreshed = repo.get(str(path.id))
    assert refreshed is not None
    assert refreshed.trust == original_trust
    assert refreshed.hit_count == original_hits


def test_no_autonomous_call_when_no_candidates(
    service: LearnedPathRetrievalService,
) -> None:
    intent = TaskIntent(raw_text="nonexistent task")
    candidates = service.retrieve_candidates(intent)
    assert candidates == []


# ---------------------------------------------------------------------------
# Contract rules
# ---------------------------------------------------------------------------


def test_retrieval_module_does_not_import_replay_autonomous_or_llm() -> None:
    import inspect

    from app.services.task_planning import retrieval as retrieval_module

    source = inspect.getsource(retrieval_module)
    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"retrieval.py imports {token}"


def test_candidate_has_no_identity_or_tenant_fields(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(repo, scenario="login")
    intent = TaskIntent(raw_text="login")
    candidates = service.retrieve_candidates(intent)
    forbidden = {"user", "account", "tenant", "user_id", "account_id", "tenant_id"}
    assert forbidden.isdisjoint(type(candidates[0]).model_fields)


# ---------------------------------------------------------------------------
# Tokenizer unit tests
# ---------------------------------------------------------------------------


def test_tokenize_extracts_lowercase_words() -> None:
    assert _tokenize("Export Users") == {"export", "users"}


def test_tokenize_returns_empty_set_for_none() -> None:
    assert _tokenize(None) == set()


def test_tokenize_returns_empty_set_for_empty_string() -> None:
    assert _tokenize("") == set()


def test_tokenize_splits_on_punctuation() -> None:
    assert _tokenize("users/export") == {"users", "export"}


def test_tokenize_handles_cjk_characters() -> None:
    # Python's \w matches Unicode word characters, so CJK sequences stay
    # intact as a single token rather than being split character-by-character.
    tokens = _tokenize("登录")
    assert "登录" in tokens


# ---------------------------------------------------------------------------
# CJK substring overlap unit tests
# ---------------------------------------------------------------------------


def test_cjk_substring_overlap_matches_contained_text() -> None:
    assert _cjk_substring_overlap("用户登录", "用户登录流程") == {"用户登录"}


def test_cjk_substring_overlap_matches_when_query_shorter() -> None:
    assert _cjk_substring_overlap("登录", "登录用户") == {"登录"}


def test_cjk_substring_overlap_empty_when_no_common_cjk() -> None:
    assert _cjk_substring_overlap("export users", "登录") == set()


def test_cjk_substring_overlap_skips_latin_tokens() -> None:
    assert _cjk_substring_overlap("login 用户", "用户 user") == {"用户"}


# ---------------------------------------------------------------------------
# CJK retrieval integration tests
# ---------------------------------------------------------------------------


def test_chinese_task_text_matches_candidate_scenario(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    matching = _make_path(
        repo, scenario="用户登录流程", page_template="/login", trust=TrustStatus.PROVISIONAL
    )
    non_matching = _make_path(
        repo, scenario="订单导出", page_template="/orders", trust=TrustStatus.PROVISIONAL
    )

    intent = TaskIntent(raw_text="用户登录")
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].learned_path_id == str(matching.id)
    assert candidates[1].learned_path_id == str(non_matching.id)
    assert any("CJK text overlap" in r for r in candidates[0].match_reasons)


def test_chinese_query_substring_matches_shorter_scenario(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    """A shorter CJK query (e.g. '登录') should match a longer scenario ('登录用户')."""
    matching = _make_path(
        repo, scenario="登录用户流程", page_template="/login", trust=TrustStatus.PROVISIONAL
    )
    _make_path(
        repo, scenario="注册账号", page_template="/register", trust=TrustStatus.PROVISIONAL
    )

    intent = TaskIntent(raw_text="登录")
    candidates = service.retrieve_candidates(intent)
    assert candidates[0].learned_path_id == str(matching.id)
    assert any("CJK text overlap" in r for r in candidates[0].match_reasons)


def test_exact_cjk_overlap_is_not_double_counted_as_keyword_overlap(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    _make_path(repo, scenario="登录", page_template="/login", trust=TrustStatus.PROVISIONAL)

    intent = TaskIntent(raw_text="登录")
    candidates = service.retrieve_candidates(intent)

    assert any("CJK text overlap" in r for r in candidates[0].match_reasons)
    assert not any("Keyword overlap" in r for r in candidates[0].match_reasons)


# ---------------------------------------------------------------------------
# Stable tie-breaker sorting
# ---------------------------------------------------------------------------


def test_same_score_sorting_is_stable_by_id(
    repo: LearnedPathRepository,
    service: LearnedPathRetrievalService,
) -> None:
    """When scores are identical, ordering must be deterministic (by id)."""
    # Two paths with identical trust, no scenario/page hints, no keyword overlap.
    _make_path(
        repo, scenario="alpha", page_template="/a", trust=TrustStatus.PROVISIONAL, hit_count=1
    )
    _make_path(
        repo, scenario="beta", page_template="/b", trust=TrustStatus.PROVISIONAL, hit_count=1
    )

    intent = TaskIntent(raw_text="unrelated text with no overlap")
    candidates = service.retrieve_candidates(intent)

    # Both should be present with identical base scores (trust=provisional +10,
    # hit_count=1 → +1).  No scenario/page/keyword overlap.  Same score.
    assert len(candidates) == 2
    ids = [c.learned_path_id for c in candidates]
    # Deterministic order: lower id comes first because tie-breaker is id asc.
    assert ids == sorted(ids)
