"""Deterministic terminal-state hints from PageAnalysis."""

from __future__ import annotations

from app.schemas.page_analysis import DiscoveredElement, PageAnalysis
from app.schemas.terminal_hints import (
    CandidateTerminalStateHint,
    PageRegionHint,
    PageTerminalHintSet,
    PossiblePageFunction,
)


def _element_text(element: DiscoveredElement) -> str:
    return " ".join(
        part
        for part in [
            element.label_text,
            element.text,
            element.aria_label,
            element.placeholder,
            element.content_hint,
            element.semantic_role,
            element.element_type,
        ]
        if part
    ).lower()


def _has_any(elements: list[DiscoveredElement], needles: tuple[str, ...]) -> bool:
    return any(any(needle in _element_text(element) for needle in needles) for element in elements)


def _region(region_id: str, region_type: str, summary: str) -> PageRegionHint:
    return PageRegionHint(region_id=region_id, region_type=region_type, summary=summary)


def _function(
    function_id: str,
    function_type: str,
    label: str,
    *,
    related_regions: list[str],
) -> PossiblePageFunction:
    return PossiblePageFunction(
        function_id=function_id,
        function_type=function_type,
        label=label,
        related_regions=related_regions,
    )


def _terminal(
    function_id: str,
    terminal_type: str,
    evidence_hint: str,
) -> CandidateTerminalStateHint:
    return CandidateTerminalStateHint(
        function_id=function_id,
        terminal_type=terminal_type,  # type: ignore[arg-type]
        evidence_hint=evidence_hint,
    )


def build_page_terminal_hints(analysis: PageAnalysis) -> PageTerminalHintSet:
    """Build semantic terminal hints without selectors or browser steps."""
    fillable = list(analysis.fillable)
    submit = list(analysis.submit)
    clickable = list(analysis.clickable)
    navigation = list(analysis.navigation)
    select = list(analysis.select)
    toggle = list(analysis.toggle)

    regions: list[PageRegionHint] = []
    functions: list[PossiblePageFunction] = []
    terminals: list[CandidateTerminalStateHint] = []

    if fillable or select or toggle:
        regions.append(
            _region(
                "filter_or_form_region",
                "filter_or_form",
                (
                    f"{len(fillable)} fillable, {len(select)} select and "
                    f"{len(toggle)} toggle controls."
                ),
            )
        )
    if submit or clickable:
        regions.append(
            _region(
                "action_region",
                "action_bar",
                f"{len(submit) + len(clickable)} actionable buttons or clickable controls.",
            )
        )
    if navigation:
        regions.append(
            _region(
                "navigation_region",
                "navigation",
                f"{len(navigation)} navigation controls.",
            )
        )

    search_signals = (
        any(element.semantic_role == "search" for element in fillable)
        or _has_any(fillable + submit + clickable, ("search", "filter", "查询", "搜索", "筛选"))
        or bool((select or toggle) and (submit or clickable))
    )
    if search_signals:
        functions.append(
            _function(
                "search_or_filter",
                "search_filter",
                "Search or filter visible records.",
                related_regions=["filter_or_form_region", "action_region"],
            )
        )
        terminals.extend(
            [
                _terminal("search_or_filter", "list_refresh", "Result/list region may refresh."),
                _terminal(
                    "search_or_filter",
                    "network_completion",
                    "Search/filter request may complete without large DOM change.",
                ),
                _terminal(
                    "search_or_filter",
                    "region_changed",
                    "Applied filters, result count or table rows may change.",
                ),
            ]
        )

    form_signals = bool(fillable and submit and not search_signals)
    if form_signals:
        functions.append(
            _function(
                "submit_form",
                "submit_form",
                "Submit a form-like operation.",
                related_regions=["filter_or_form_region", "action_region"],
            )
        )
        terminals.extend(
            [
                _terminal("submit_form", "navigation", "Successful submit may navigate."),
                _terminal(
                    "submit_form",
                    "toast_or_status_message",
                    "Successful submit may show a status message.",
                ),
                _terminal("submit_form", "region_changed", "Form/result region may update."),
            ]
        )

    if _has_any(clickable + submit, ("download", "export", "导出", "下载", "excel", "csv")):
        functions.append(
            _function(
                "export_or_download",
                "export_download",
                "Export or download page data.",
                related_regions=["action_region"],
            )
        )
        terminals.extend(
            [
                _terminal(
                    "export_or_download",
                    "download_started",
                    "Browser download event may start.",
                ),
                _terminal(
                    "export_or_download",
                    "network_completion",
                    "Export request may complete before file metadata is available.",
                ),
            ]
        )

    if navigation:
        functions.append(
            _function(
                "navigate_or_open_detail",
                "navigation_or_detail",
                "Navigate or open detail content.",
                related_regions=["navigation_region"],
            )
        )
        terminals.extend(
            [
                _terminal(
                    "navigate_or_open_detail",
                    "navigation",
                    "URL, title or frame may change.",
                ),
                _terminal(
                    "navigate_or_open_detail",
                    "modal_or_popup_opened",
                    "Detail action may open a modal, drawer or popup.",
                ),
            ]
        )

    if not functions:
        functions.append(
            _function(
                "operate_page",
                "unknown",
                "Operate page with insufficient semantic terminal hints.",
                related_regions=[],
            )
        )
        terminals.append(
            _terminal(
                "operate_page",
                "no_observable_change",
                "No strong terminal-state hint could be derived.",
            )
        )

    if len(functions) > 1:
        confidence = 0.75
        source = "deterministic"
    elif functions[0].function_type != "unknown":
        confidence = 0.6
        source = "deterministic"
    else:
        confidence = 0.35
        source = "fallback"

    page_purpose = f"{analysis.title or analysis.url} page"
    page_content_summary = (
        f"{analysis.total_visible} visible controls; "
        f"{len(fillable)} fillable, {len(submit)} submit, {len(clickable)} clickable, "
        f"{len(navigation)} navigation, {len(select)} select, {len(toggle)} toggle."
    )
    return PageTerminalHintSet(
        page_purpose=page_purpose,
        page_content_summary=page_content_summary,
        page_regions=regions,
        possible_functions=functions,
        candidate_terminal_states=terminals,
        confidence=confidence,
        reason_summary="deterministic hints derived from PageAnalysis categories and labels",
        source=source,  # type: ignore[arg-type]
    )
