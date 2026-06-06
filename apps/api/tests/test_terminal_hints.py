from __future__ import annotations

from app.schemas.page_analysis import DiscoveredElement, PageAnalysis
from app.services.learning.terminal_hints import build_page_terminal_hints


def _element(
    category: str,
    *,
    text: str = "",
    label_text: str | None = None,
    semantic_role: str | None = None,
    selector: str = "#secret-selector",
    content_hint: str | None = None,
) -> DiscoveredElement:
    return DiscoveredElement(
        category=category,  # type: ignore[arg-type]
        tag="button" if category in {"submit", "clickable", "navigation"} else "input",
        text=text,
        label_text=label_text,
        semantic_role=semantic_role,  # type: ignore[arg-type]
        selector=selector,
        content_hint=content_hint,
    )


def _analysis(**overrides) -> PageAnalysis:
    defaults = {
        "url": "https://example.invalid/page",
        "title": "Users",
        "total_visible": 3,
        "total_hidden": 0,
        "fillable": [],
        "submit": [],
        "clickable": [],
        "navigation": [],
        "select": [],
        "toggle": [],
        "other": [],
    }
    defaults.update(overrides)
    return PageAnalysis(**defaults)


def _terminal_types(hints) -> set[str]:
    return {item.terminal_type for item in hints.candidate_terminal_states}


def _function_types(hints) -> set[str]:
    return {item.function_type for item in hints.possible_functions}


def test_search_page_generates_list_refresh_and_network_completion_hints() -> None:
    hints = build_page_terminal_hints(
        _analysis(
            fillable=[_element("fillable", label_text="Search", semantic_role="search")],
            submit=[_element("submit", text="Search")],
        )
    )

    assert "search_filter" in _function_types(hints)
    assert {"list_refresh", "network_completion", "region_changed"} <= _terminal_types(hints)
    assert hints.source == "deterministic"
    assert hints.confidence >= 0.6


def test_form_page_generates_submit_hints_when_not_search() -> None:
    hints = build_page_terminal_hints(
        _analysis(
            title="Create",
            fillable=[_element("fillable", label_text="Name", semantic_role="name")],
            submit=[_element("submit", text="Save")],
        )
    )

    assert "submit_form" in _function_types(hints)
    assert {"navigation", "toast_or_status_message", "region_changed"} <= _terminal_types(hints)


def test_export_control_generates_download_hint() -> None:
    hints = build_page_terminal_hints(
        _analysis(clickable=[_element("clickable", text="Export CSV")])
    )

    assert "export_download" in _function_types(hints)
    assert "download_started" in _terminal_types(hints)


def test_navigation_control_generates_navigation_and_modal_hints() -> None:
    hints = build_page_terminal_hints(
        _analysis(navigation=[_element("navigation", text="Details")])
    )

    assert "navigation_or_detail" in _function_types(hints)
    assert {"navigation", "modal_or_popup_opened"} <= _terminal_types(hints)


def test_no_control_page_uses_low_confidence_fallback() -> None:
    hints = build_page_terminal_hints(_analysis(total_visible=0))

    assert hints.source == "fallback"
    assert hints.confidence == 0.35
    assert _function_types(hints) == {"unknown"}
    assert _terminal_types(hints) == {"no_observable_change"}


def test_terminal_hints_do_not_emit_selectors_or_raw_dom_paths() -> None:
    hints = build_page_terminal_hints(
        _analysis(
            fillable=[
                _element(
                    "fillable",
                    label_text="Search",
                    semantic_role="search",
                    selector="#users .secret input",
                )
            ],
            submit=[_element("submit", text="Search", selector="button[data-secret]")],
        )
    )

    payload = hints.model_dump(mode="json")
    text = str(payload)
    assert "selector" not in text
    assert "target_selector" not in text
    assert "#users" not in text
    assert "data-secret" not in text
