"""Page understanding service (Phase 6C).

Analyzes a PageContext and produces a structured PageUnderstanding result
by calling the LLM provider layer.

Usage:
    from app.services.page_understanding import generate_page_understanding

    result = generate_page_understanding(page_context)
    if result.ok:
        understanding = result.parsed  # PageUnderstanding dict
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.locale import get_locale
from app.schemas.agent_input import PageContext
from app.schemas.page_understanding import PAGE_UNDERSTANDING_SCHEMA, PageUnderstanding
from app.services.llm_provider import build_request, generate_structured

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_BASE = """\
You are a page structure analyst. Your job is to look at a web page's DOM \
structure (provided as a simplified AST) and produce a structured understanding \
of what the page is, what it does, and what its key parts are.

Rules:
- Be concise. One sentence per field where indicated.
- page_kind must be one of: list, form, detail, dashboard, config, modal, login, mixed, unknown.
- primary_regions: identify the 2-6 most important regions. Do not list every node.
- primary_actions: list the main action entry points (buttons, links that trigger operations). \
  Do not exhaustively list every clickable element.
- key_entities: extract the core business objects that appear on the page (e.g. "order", "product"). \
  Keep to 1-5 items. Output empty list if unclear.
- confidence_notes: only add notes when a judgment is genuinely uncertain. Usually empty.\
"""

_LOCALE_INSTRUCTIONS: dict[str, str] = {
    "zh": "All text output MUST be in Chinese (简体中文).",
    "en": "All text output MUST be in English.",
    "ja": "All text output MUST be in Japanese (日本語).",
}


def _build_system_prompt(locale: str = "en") -> str:
    lang_line = _LOCALE_INSTRUCTIONS.get(locale, _LOCALE_INSTRUCTIONS["en"])
    return f"{_SYSTEM_PROMPT_BASE}\n- {lang_line}"


def _build_ast_summary(page: PageContext) -> str:
    """Serialize the AST to a compact text representation for the prompt."""
    if not page.ast_nodes:
        return "(empty page — no AST nodes)"

    # Serialize as compact JSON — the LLM needs structure, not pretty-print
    nodes_json = json.dumps(
        [n.model_dump(exclude_none=True, exclude_defaults=True) for n in page.ast_nodes],
        ensure_ascii=False,
        separators=(",", ":"),
    )

    # Truncate if very large (keep within reasonable prompt size)
    max_len = 60_000
    if len(nodes_json) > max_len:
        nodes_json = nodes_json[:max_len] + "\n... (truncated)"

    return nodes_json


def build_page_understanding_prompt(page: PageContext) -> str:
    """Build the user prompt from a PageContext.

    Exposed for testing — tests can verify prompt structure without
    calling the LLM.
    """
    ast_summary = _build_ast_summary(page)

    parts = [
        f"Page URL: {page.url}" if page.url else None,
        f"Page title: {page.title}" if page.title else None,
        f"Total nodes: {page.total_node_count}, elements: {page.element_count}, "
        f"visible elements: {page.visible_element_count}, "
        f"top-level regions: {page.top_level_count}",
    ]

    if page.interactive_element_tags:
        tags_str = ", ".join(f"{k}: {v}" for k, v in sorted(page.interactive_element_tags.items()))
        parts.append(f"Interactive elements: {tags_str}")

    parts.append(f"\nSimplified AST:\n{ast_summary}")

    return "\n".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_page_understanding(
    page: PageContext,
    *,
    locale: str | None = None,
) -> dict[str, Any]:
    """Generate a structured page understanding from a PageContext.

    Returns a dict with:
        - "ok": bool
        - "understanding": PageUnderstanding dict (when ok=True)
        - "error": error info (when ok=False)
        - "usage": token usage info
    """
    resolved_locale = locale or get_locale()
    prompt = build_page_understanding_prompt(page)

    request = build_request(
        prompt,
        system=_build_system_prompt(resolved_locale),
        response_schema=PAGE_UNDERSTANDING_SCHEMA,
    )

    resp = generate_structured(request)

    if not resp.ok:
        logger.warning("Page understanding failed: %s", resp.error)
        return {
            "ok": False,
            "understanding": None,
            "error": resp.error.model_dump() if resp.error else {"kind": "unknown", "message": "Unknown error"},
            "usage": resp.usage.model_dump(),
        }

    # Validate against Pydantic model
    try:
        validated = PageUnderstanding.model_validate(resp.parsed)
    except Exception as exc:
        logger.warning("Page understanding schema validation failed: %s", exc)
        return {
            "ok": False,
            "understanding": resp.parsed,  # return raw parsed for debugging
            "error": {"kind": "validation_error", "message": str(exc)},
            "usage": resp.usage.model_dump(),
        }

    return {
        "ok": True,
        "understanding": validated.model_dump(),
        "error": None,
        "usage": resp.usage.model_dump(),
    }
