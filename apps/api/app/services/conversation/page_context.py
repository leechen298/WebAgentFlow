"""Page context bundle builder for M11.3.5 routing."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ast import FullAST, SimplifiedAST
from app.schemas.page_analysis import DiscoveredElement, PageAnalysis
from app.services.ast_simplifier import simplify_ast
from app.services.html_ast_parser import parse_html
from app.services.learning import page_signature


class PageContextBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    title: str | None = None
    visible_text_summary: str | None = None
    interactive_elements: list[dict[str, Any]] = Field(default_factory=list)
    full_ast: FullAST
    simplified_ast: SimplifiedAST
    page_signature: dict[str, Any] = Field(default_factory=dict)
    screenshot_ref: str | None = None
    learned_actions: list[dict[str, Any]] = Field(default_factory=list)


class PageContextBuilder:
    """Build page context from runtime evidence.

    Unit tests can call ``build_from_html`` without a browser. Runtime callers
    may call ``build_from_runtime`` after code has already decided inspection is
    allowed.
    """

    def build_from_html(
        self,
        *,
        url: str,
        html: str,
        title: str | None = None,
        analysis: PageAnalysis | None = None,
        learned_actions: list[dict[str, Any]] | None = None,
    ) -> PageContextBundle:
        full_ast = parse_html(html)
        simplified_ast = simplify_ast(full_ast)
        elements = _interactive_element_summary(analysis) if analysis else []
        signature = (
            page_signature.build_signature_dict(url=url, analysis=analysis)
            if analysis is not None
            else {
                "page_template": page_signature.path_template(url),
                "query_signature": page_signature.query_signature(url),
                "dom_fingerprint": None,
            }
        )
        return PageContextBundle(
            url=url,
            title=title or (analysis.title if analysis else None),
            visible_text_summary=_visible_text_summary(full_ast.model_dump(mode="json")),
            interactive_elements=elements,
            full_ast=full_ast,
            simplified_ast=simplified_ast,
            page_signature=signature,
            screenshot_ref=analysis.screenshot_ref if analysis else None,
            learned_actions=learned_actions or [],
        )

    def build_from_runtime(
        self,
        runtime: Any,
        *,
        analysis: PageAnalysis | None = None,
        learned_actions: list[dict[str, Any]] | None = None,
    ) -> PageContextBundle:
        return self.build_from_html(
            url=runtime.current_url(),
            title=runtime.current_title(),
            html=runtime.current_html(),
            analysis=analysis,
            learned_actions=learned_actions,
        )


def build_runtime_page_context_provider():
    builder = PageContextBuilder()

    def provider(
        *,
        route_decision: Any,
        intake: Any,
        headless: bool,
    ) -> PageContextBundle | None:
        target_url = route_decision.target.url or intake.target.url
        if not target_url:
            return None

        from app.services.execution.execution_runtime import (
            ExecutionRuntime,
            RuntimeConfig,
        )
        from app.services.learning.page_analyzer import analyze_page

        try:
            with ExecutionRuntime(RuntimeConfig(headless=headless)) as runtime:
                runtime.navigate(target_url)
                analysis = analyze_page(runtime)
                return builder.build_from_runtime(runtime, analysis=analysis)
        except Exception:
            return None

    return provider


def _interactive_element_summary(analysis: PageAnalysis) -> list[dict[str, Any]]:
    elements: list[DiscoveredElement] = [
        *analysis.fillable,
        *analysis.submit,
        *analysis.clickable,
        *analysis.navigation,
        *analysis.select,
        *analysis.toggle,
        *analysis.other,
    ]
    return [
        {
            "category": element.category,
            "tag": element.tag,
            "role": element.role,
            "label": element.label_text
            or element.aria_label
            or element.placeholder
            or element.text
            or element.content_hint,
            "semantic_role": element.semantic_role,
        }
        for element in elements
        if element.visible
    ]


def _visible_text_summary(value: Any, *, limit: int = 500) -> str:
    parts: list[str] = []

    def walk(node: Any) -> None:
        if len(" ".join(parts)) >= limit:
            return
        if isinstance(node, dict):
            if node.get("node_type") == "text" and node.get("text"):
                parts.append(str(node["text"]))
            for child in node.get("children") or []:
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(value.get("nodes") if isinstance(value, dict) else value)
    return " ".join(parts)[:limit]
