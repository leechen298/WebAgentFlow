"""AST parsing endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.ast import FullAST, SimplifiedAST
from app.schemas.common import ApiResponse
from app.services.ast_simplifier import simplify_ast
from app.services.html_ast_parser import parse_html

router = APIRouter(prefix="/ast", tags=["ast"])


class ParseHtmlRequest(BaseModel):
    """Request body for HTML → Full AST parsing."""

    html: str
    """HTML string to parse (fragment or full document)."""

    iframe_html: dict[str, str] | None = None
    """Optional mapping of iframe identifiers (src URL or data-frame-id)
    to their HTML content strings."""


@router.post("/parse", response_model=ApiResponse[FullAST])
def parse_html_to_ast(payload: ParseHtmlRequest) -> ApiResponse[FullAST]:
    """Parse HTML into a Full AST.

    Accepts raw HTML and returns a faithful DOM-structure-preserving AST.
    No semantic interpretation or restructuring is performed.
    """
    result = parse_html(payload.html, iframe_html=payload.iframe_html)
    return ApiResponse(data=result)


@router.post("/simplify", response_model=ApiResponse[SimplifiedAST])
def simplify_html_to_ast(payload: ParseHtmlRequest) -> ApiResponse[SimplifiedAST]:
    """Parse HTML and produce a Simplified AST.

    Parses raw HTML into a Full AST, then applies structure-preserving
    simplification: class token filtering + attribute pruning.
    Tree structure is unchanged.
    """
    full = parse_html(payload.html, iframe_html=payload.iframe_html)
    result = simplify_ast(full)
    return ApiResponse(data=result)
